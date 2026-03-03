from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from cosinnus.conf import settings
from cosinnus.models.conference import CosinnusConferenceSettings


class CosinnusConferenceBBBParamsSerializer(serializers.Serializer):
    """
    Serializer for conference setting BBB parameter.
    Note: We currently do not expose the "inherit" value of BBB parameters.
    """

    mic_starts_on = serializers.BooleanField(label='"Turn on microphone on entering')
    cam_starts_on = serializers.BooleanField(label='Turn on camera on entering')
    waiting_room = serializers.BooleanField(label='Require moderator approval before joning')
    record_meeting = serializers.BooleanField(label='Allow recording')
    welcome_message = serializers.CharField(label='Define a custom welcome message')

    # initialized via kwargs
    parent_object = None
    group = None

    def __init__(self, instance=None, **kwargs):
        self.parent_object = kwargs.pop('parent_object')
        self.group = kwargs.pop('group')
        super().__init__(instance, **kwargs)
        # set initial bbb param field values from conference settings
        conference_settings = self.parent_object.get_conference_settings_object()
        bbb_params = conference_settings.get_bbb_preset_form_field_values()
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.BooleanField):
                field.initial = True if bbb_params.get(field_name, 0) == 1 else False
            else:
                field.initial = bbb_params.get(field_name, '')

        # remove disabled fields
        disabled_fields = []
        for field_name, field in self.fields.items():
            if field_name not in settings.BBB_PRESET_USER_FORM_FIELDS:
                disabled_fields.append(field_name)
        for field_name in disabled_fields:
            del self.fields[field_name]

        # make premium field not required if group is not premium, as we do not allow commiting them during validation
        # note: using read_only does not work for non-model serializer
        # note: we do not remove the field complete to be able to show the potential setting in the frontend
        if settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED and not self.group.is_premium_ever:
            for field_name in settings.BBB_PRESET_USER_FORM_FIELDS_PREMIUM_ONLY:
                self.fields[field_name].required = False

    def validate(self, data):
        # do not allow setting premium fields if group is not premium
        if settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED and not self.group.is_premium_ever:
            for field_name in settings.BBB_PRESET_USER_FORM_FIELDS_PREMIUM_ONLY:
                if field_name in self.initial_data:
                    raise serializers.ValidationError(f'Not allowed to set premium field "{field_name}"')
        return data


class CosinnusConferenceSettingsSerializer(serializers.Serializer):
    """
    Serializer for ConferenceSettings, BBB parameters and conference related settings.
    """

    bbb_params = serializers.JSONField(required=False, label='Conference Setting BBB parameters')
    premium_params = serializers.JSONField(required=False, label='Premium only BBB parameters')
    show_guest_access = serializers.BooleanField(
        required=False, label='Show guest access link outside of a running conference'
    )

    # parameters initialized via kwargs
    parent_object = None
    group = None

    def __init__(self, instance=None, **kwargs):
        self.parent_object = kwargs.pop('parent_object')
        self.group = kwargs.pop('group')
        super().__init__(instance, **kwargs)
        # initialize fields
        self.fields['bbb_params'].initial = self.get_bbb_params_initial()
        self.fields['premium_params'].initial = self.get_premium_params_initial()
        self.fields['show_guest_access'].initial = self.get_show_guest_access_initial()

    def get_bbb_params_initial(self):
        """Initialize BBB parameters using the respective serializer."""
        bbb_params_serializer = CosinnusConferenceBBBParamsSerializer(
            parent_object=self.parent_object, group=self.group
        )
        return bbb_params_serializer.data

    def get_premium_params_initial(self):
        """Initialize premium bbb parameter from settings."""
        premium_params = []
        if settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED:
            premium_params = settings.BBB_PRESET_USER_FORM_FIELDS_PREMIUM_ONLY
        return premium_params

    def get_show_guest_access_initial(self):
        """Initialize show guest access setting from media_tag field."""
        return self.parent_object.media_tag.show_bbb_guest_access_outside_of_conference

    def validate(self, data):
        bbb_param_data = data.get('bbb_params')
        if bbb_param_data:
            # validate bbb parameters using the respective serliazer.
            bbb_param_serializer = CosinnusConferenceBBBParamsSerializer(
                data=bbb_param_data,
                parent_object=self.parent_object,
                group=self.group,
            )
            bbb_param_serializer.is_valid(raise_exception=True)
        return data

    def save(self, **kwargs):
        # save all settings
        self.save_conference_settings()
        self.save_parent_settings()

    def save_conference_settings(self):
        """Save BBB parameters in conference settings."""
        bbb_params = self.validated_data.get('bbb_params')
        if bbb_params:
            conference_settings = self.parent_object.conference_settings_assignments.first() or None
            if not conference_settings:
                # create conference settings
                conference_settings = CosinnusConferenceSettings()
                content_type = ContentType.objects.get_for_model(self.parent_object._meta.model)
                conference_settings.content_type = content_type
                conference_settings.object_id = self.parent_object.id
                conference_settings.bbb_nature = self.parent_object.get_bbb_room_nature()
                conference_settings.is_premium_ever = getattr(self.group, 'is_premium_ever', False)

            # get preset choices from submitted data
            preset_choices = {}
            for bbb_param, value in bbb_params.items():
                if isinstance(value, bool):
                    preset_choices[bbb_param] = 1 if value is True else 0
                else:
                    preset_choices[bbb_param] = value

            # set BBB parameters from presets
            conference_settings.set_bbb_preset_form_field_values(preset_choices)

            # save object and clear the cache
            conference_settings.save()
            conference_settings.clear_get_for_object_cache(self.parent_object)

    def save_parent_settings(self):
        """Save settings in the parent instance."""
        show_guest_access = self.validated_data.get('show_guest_access')
        if show_guest_access is not None:
            # set metia_tag show_bbb_guest_access_outside_of_conference field.
            self.parent_object.media_tag.show_bbb_guest_access_outside_of_conference = show_guest_access
            self.parent_object.media_tag.save()
