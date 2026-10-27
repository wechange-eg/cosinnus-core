from rest_framework import serializers

from cosinnus.models.personal_dashboard import (
    get_personal_dashboard_widget,
    get_personal_dashboard_widget_ids,
)
from cosinnus.models.user_dashboard_announcement import (
    UserDashboardAnnouncement,
    UserDashboardAnnouncementCallToActionButton,
    UserDashboardWelcomeAnnouncement,
    UserDashboardWelcomeAnnouncementCallToActionButton,
)


class CosinnusPersonalDashboardWidgetSerializer(serializers.Serializer):
    """Readonly serializer for the v3 personal dashboard widgets."""

    id = serializers.CharField()
    active = serializers.BooleanField(required=False)
    display = serializers.JSONField(required=False)
    api_url = serializers.URLField(read_only=True)
    data = serializers.JSONField(read_only=True)
    has_more = serializers.BooleanField(read_only=True)
    conf = serializers.JSONField(read_only=True)

    def to_representation(self, instance):
        request = self.context['request']
        user = request.user
        ret = super().to_representation(instance)
        # populate user related fields from the widget
        data, has_more = instance.get_data(request)
        ret.update(
            {
                'active': instance.is_active(user),
                'display': instance.get_display(user),
                'data': data,
                'has_more': has_more,
                'conf': instance.get_conf(user),
            }
        )
        return ret


class CosinnusPersonalDashboardWidgetSettingsSerializer(serializers.Serializer):
    """Serializer for the v3 "active" and "display" settings of personal dashboard widgets."""

    id = serializers.CharField()
    active = serializers.BooleanField(required=False)
    display = serializers.JSONField(required=False)

    def validate(self, attrs):
        # check widget id is valid
        widget_id = attrs.get('id')
        if not widget_id:
            raise serializers.ValidationError({'id': 'This field is required.'})
        elif widget_id not in get_personal_dashboard_widget_ids():
            raise serializers.ValidationError({'id': 'Unknown widget id.'})
        return attrs

    def create(self, validated_data):
        """Save user widget settings."""
        user = self.context['request'].user
        widget = get_personal_dashboard_widget(validated_data['id'])
        if 'active' in validated_data:
            widget.set_active(user, validated_data['active'])
        if 'display' in validated_data:
            widget.set_display(user, validated_data['display'])


class CosinnusPersonalDashboardAnnouncementCallToActionButtonSerializer(serializers.ModelSerializer):
    """Serializer for dashboard announcement call-to-action buttons."""

    class Meta:
        model = UserDashboardAnnouncementCallToActionButton
        fields = (
            'label',
            'url',
        )


class CosinnusPersonalDashboardAnnouncementSerializerMixin:
    """Mixin for dashboard and welcome announcement."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # reset image and text field depending on display option
        if instance.display == UserDashboardAnnouncement.DISPLAY_IMAGE_AND_TEXT:
            data['text_col_1'] = None
            data['text_col_2'] = None
        else:
            data['image'] = None
            data['text'] = None

        # hide cta buttons if disabled
        if not instance.call_to_action_active:
            data['cta_buttons'] = None
        return data


class CosinnusPersonalDashboardAnnouncementSerializer(
    CosinnusPersonalDashboardAnnouncementSerializerMixin, serializers.ModelSerializer
):
    """Serializer for the dashboard user announcements."""

    id = serializers.IntegerField()
    category = serializers.CharField(source='get_category_display', read_only=True)
    cta_buttons = CosinnusPersonalDashboardAnnouncementCallToActionButtonSerializer(
        source='call_to_action_buttons', many=True, read_only=True
    )
    dismissed = serializers.BooleanField(write_only=True)

    class Meta:
        model = UserDashboardAnnouncement
        fields = (
            'id',
            'title',
            'category',
            'display',
            'image',
            'text',
            'text_col_1',
            'text_col_2',
            'cta_buttons',
            'dismissed',
        )
        read_only_fields = (
            'title',
            'display',
            'image',
            'text',
            'text_col_1',
            'text_col_2',
            'cta_buttons',
        )

    def validate(self, attrs):
        # check announcement id is passed for dismissing
        announcement_id = attrs.get('id')
        if not announcement_id:
            raise serializers.ValidationError({'id': 'This field is required.'})
        elif not UserDashboardAnnouncement.objects.filter(pk=announcement_id).exists():
            raise serializers.ValidationError({'id': 'Announcement does not exist.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # handle "none" category type
        if instance.category == 0:
            data['category'] = None
        return data

    def save(self, **kwargs):
        """Dismiss announcement."""
        user = self.context['request'].user
        if self.validated_data['dismissed']:
            UserDashboardAnnouncement.hide_for_user(user, self.validated_data['id'])


class CosinnusPersonalDashboardWelcomeAnnouncementCallToActionButtonSerializer(serializers.ModelSerializer):
    """Serializer for dashboard welcome announcement call-to-action buttons."""

    class Meta:
        model = UserDashboardWelcomeAnnouncementCallToActionButton
        fields = (
            'label',
            'url',
        )


class CosinnusPersonalDashboardWelcomeAnnouncementSerializer(
    CosinnusPersonalDashboardAnnouncementSerializerMixin, serializers.ModelSerializer
):
    """Serializer for the dashboard welcome announcements."""

    cta_buttons = CosinnusPersonalDashboardWelcomeAnnouncementCallToActionButtonSerializer(
        source='call_to_action_buttons', many=True, read_only=True
    )
    dismissed = serializers.BooleanField(write_only=True)

    class Meta:
        model = UserDashboardWelcomeAnnouncement
        fields = (
            'title',
            'display',
            'image',
            'text',
            'text_col_1',
            'text_col_2',
            'cta_buttons',
            'dismissed',
        )
        read_only_fields = (
            'title',
            'display',
            'image',
            'text',
            'text_col_1',
            'text_col_2',
            'cta_buttons',
        )

    def save(self, **kwargs):
        """Dismiss welcome announcement"""
        user = self.context['request'].user
        if self.validated_data['dismissed']:
            UserDashboardWelcomeAnnouncement.hide_for_user(user)
