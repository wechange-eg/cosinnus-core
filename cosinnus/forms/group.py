# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import io
import re
from builtins import object, str
from copy import copy
from uuid import uuid1

import chardet
from annoying.functions import get_object_or_None
from awesome_avatar import forms as avatar_forms
from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth import get_user_model
from django.forms.widgets import SelectMultiple
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_select2.fields import HeavyModelSelect2MultipleChoiceField
from django_select2.widgets import Select2MultipleWidget

from cosinnus import cosinnus_notifications
from cosinnus.conf import settings
from cosinnus.core.registries.apps import app_registry
from cosinnus.fields import GroupSelect2MultipleChoiceField, UserSelect2MultipleChoiceField
from cosinnus.forms.attached_object import FormAttachableMixin
from cosinnus.forms.dynamic_fields import _DynamicFieldsBaseFormMixin
from cosinnus.forms.managed_tags import ManagedTagFormMixin
from cosinnus.forms.mixins import AdditionalFormsMixin
from cosinnus.forms.translations import TranslatedFieldsFormMixin
from cosinnus.forms.widgets import SplitHiddenDateWidget
from cosinnus.models import UserBlock
from cosinnus.models.group import (
    SDG_CHOICES,
    CosinnusBaseGroup,
    CosinnusGroupCallToActionButton,
    CosinnusGroupGalleryImage,
    CosinnusGroupMembership,
    CosinnusLocation,
    CosinnusPortal,
    RelatedGroups,
)
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.templatetags.cosinnus_tags import is_superuser
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.lanugages import MultiLanguageFieldValidationFormMixin
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.user import filter_active_users, get_group_select2_pills, get_user_select2_pills
from cosinnus.utils.validators import CleanFromToDateFieldsMixin, validate_file_infection
from cosinnus.views.facebook_integration import FacebookIntegrationGroupFormMixin
from cosinnus_organization.models import CosinnusOrganization

# matches a twitter username
TWITTER_USERNAME_VALID_RE = re.compile(r'^@?[A-Za-z0-9_]+$')
# matches (group 0) a twitter widget id from its embed HTML code
TWITTER_WIDGET_EMBED_ID_RE = re.compile(r'data-widget-id="(\d+)"')


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


class GroupKwargModelFormMixin(object):
    """
    Generic model form mixin for popping group out of the kwargs and
    attaching it to the instance.

    This mixin must precede ``forms.ModelForm`` / ``forms.Form``. The form is
    not expecting these kwargs to be passed in, so they must be popped off
    before anything else is done.
    """

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super(GroupKwargModelFormMixin, self).__init__(*args, **kwargs)
        if self.group and hasattr(self.instance, 'group_id'):
            self.instance.group_id = self.group.id


class CleanAppSettingsMixin(object):
    def clean_deactivated_apps(self):
        deactivatable_apps = app_registry.get_deactivatable_apps()
        # the form field is actually inverse, and active apps are checked
        active_apps = self.data.getlist('deactivated_apps')

        # if this is not a group, remove from the choices all apps that are group-only
        if self.instance.type != CosinnusSociety.TYPE_SOCIETY:
            active_apps = [app for app in active_apps if app not in app_registry.get_activatable_for_groups_only_apps()]

        deactivated_apps = [option_app for option_app in deactivatable_apps if option_app not in active_apps]
        return ','.join(deactivated_apps)

    def clean_microsite_public_apps(self):
        deactivatable_apps = app_registry.get_deactivatable_apps()
        # public apps are checked
        public_apps = self.data.getlist('microsite_public_apps')
        # only accept existing, deactivatable apps
        public_apps = [option_app for option_app in deactivatable_apps if option_app in public_apps]
        return ','.join(public_apps) if public_apps else '<all_deselected>'


class AsssignPortalMixin(object):
    """Assign current portal on save when created"""

    def save(self, **kwargs):
        if self.instance.pk is None:
            self.instance.portal = CosinnusPortal.get_current()
        return super(AsssignPortalMixin, self).save(**kwargs)


class GroupFormDynamicFieldsMixin(_DynamicFieldsBaseFormMixin):
    """Mixin for the CosinnusBaseGroupForm modelform that
    adds functionality for by-portal configured extra group form fields"""

    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_GROUP_EXTRA_FIELDS

    def full_clean(self):
        """Assign the extra fields to the `extra_fields` the userprofile JSON field
        instead of model fields, during regular form saving"""
        super().full_clean()
        if hasattr(self, 'cleaned_data'):
            for field_name in self.DYNAMIC_FIELD_SETTINGS.keys():
                # skip saving fields that weren't included in the POST
                # this is important, do not add exceptions here.
                # if you need an exception, add a hidden field with the field name and any value!
                if field_name not in self.data.keys():
                    continue
                # skip saving disabled fields
                if field_name in self.fields and not self.fields[field_name].disabled:
                    self.instance.dynamic_fields[field_name] = self.cleaned_data.get(field_name, None)


class CosinnusBaseGroupForm(
    TranslatedFieldsFormMixin,
    FacebookIntegrationGroupFormMixin,
    MultiLanguageFieldValidationFormMixin,
    GroupFormDynamicFieldsMixin,
    ManagedTagFormMixin,
    FormAttachableMixin,
    AdditionalFormsMixin,
    forms.ModelForm,
):
    avatar = avatar_forms.AvatarField(
        required=getattr(settings, 'COSINNUS_GROUP_AVATAR_REQUIRED', False),
        disable_preview=True,
        validators=[validate_file_infection],
    )
    website = forms.URLField(widget=forms.TextInput, required=False)
    # we want a textarea without character limit here so HTML can be pasted (will be cleaned)
    twitter_widget_id = forms.CharField(widget=forms.Textarea, required=False)
    sdgs = forms.MultipleChoiceField(choices=SDG_CHOICES, required=False)

    related_groups = forms.ModelMultipleChoiceField(queryset=get_cosinnus_group_model().objects.none())

    if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS:
        managed_tag_field = forms.CharField(required=settings.COSINNUS_MANAGED_TAGS_GROUP_FORMFIELD_REQUIRED)

    # This is for `FormAttachableMixin` to set all uploaded files to public (otherwise they couldn't be downloaded
    # from the microsite)
    # TODO: if groups ever become non-publicly visible, change this setting!
    FORCE_ATTACHED_OBJECTS_VISIBILITY_ALL = True

    class Meta(object):
        fields = (
            [
                'name',
                'public',
                'subtitle',
                'description',
                'description_long',
                'contact_info',
                'sdgs',
                'avatar',
                'wallpaper',
                'website',
                'video',
                'twitter_username',
                'twitter_widget_id',
                'flickr_url',
                'deactivated_apps',
                'microsite_public_apps',
                'call_to_action_active',
                'call_to_action_title',
                'call_to_action_description',
                'membership_mode',
                'is_open_for_cooperation',
                'use_invite_token',
            ]
            + getattr(settings, 'COSINNUS_GROUP_ADDITIONAL_FORM_FIELDS', [])
            + (['show_contact_form'] if settings.COSINNUS_ALLOW_CONTACT_FORM_ON_MICROPAGE else [])
            + (['publicly_visible'] if settings.COSINNUS_GROUP_PUBLICY_VISIBLE_OPTION_SHOWN else [])
            + (
                [
                    'facebook_group_id',
                    'facebook_page_id',
                ]
                if settings.COSINNUS_FACEBOOK_INTEGRATION_ENABLED
                else []
            )
            + (
                [
                    'embedded_dashboard_html',
                ]
                if settings.COSINNUS_GROUP_DASHBOARD_EMBED_HTML_FIELD_ENABLED
                else []
            )
            + (
                [
                    'managed_tag_field',
                ]
                if (settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS)
                else []
            )
        )

    def __init__(self, instance, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(CosinnusBaseGroupForm, self).__init__(instance=instance, *args, **kwargs)

        self.fields['related_groups'] = HeavyModelSelect2MultipleChoiceField(
            required=False,
            data_url=reverse('cosinnus:select2:groups') + ('?except=' + str(instance.pk) if instance else ''),
            queryset=get_cosinnus_group_model().objects.filter(portal_id=CosinnusPortal.get_current().id),
            initial=[] if not instance else [rel_group.pk for rel_group in instance.related_groups.all()],
        )
        if settings.COSINNUS_GROUP_DASHBOARD_EMBED_HTML_FIELD_ENABLED and not is_superuser(self.request.user):
            self.fields['embedded_dashboard_html'].disabled = True
        if not settings.COSINNUS_ENABLE_SDGS:
            del self.fields['sdgs']

        # use select2 widgets for m2m fields
        for field in list(self.fields.values()):
            if type(field.widget) is SelectMultiple:
                field.widget = Select2MultipleWidget(choices=field.choices)

        if 'video_conference_type' in self.fields:
            # dynamic dropdown for video conference types in events
            custom_choices = [
                (CosinnusBaseGroup.NO_VIDEO_CONFERENCE, _('No video conference')),
            ]
            if settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS:
                if not settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED or (
                    instance and instance.group_can_be_bbb_enabled
                ):
                    custom_choices += [
                        (CosinnusBaseGroup.BBB_MEETING, _('BBB-Meeting')),
                    ]
            if CosinnusPortal.get_current().video_conference_server:
                custom_choices += [
                    (CosinnusBaseGroup.FAIRMEETING, _('Fairmeeting')),
                ]
                self.fields['video_conference_type'].initial = CosinnusBaseGroup.FAIRMEETING
            self.fields['video_conference_type'].choices = custom_choices

        # disable the 'Create token' checkbox in case if the sought-after type of CosinnusBaseGroup has not been given
        # in settings
        if (
            CosinnusBaseGroup.TYPE_PROJECT not in settings.COSINNUS_ENABLE_USER_JOIN_TOKENS_FOR_GROUP_TYPE
            and self.instance.group_is_project
        ):
            self.fields['use_invite_token'].disabled = True
        elif (
            CosinnusBaseGroup.TYPE_SOCIETY not in settings.COSINNUS_ENABLE_USER_JOIN_TOKENS_FOR_GROUP_TYPE
            and self.instance.group_is_group
        ):
            self.fields['use_invite_token'].disabled = True
        elif (
            CosinnusBaseGroup.TYPE_CONFERENCE not in settings.COSINNUS_ENABLE_USER_JOIN_TOKENS_FOR_GROUP_TYPE
            and self.instance.group_is_conference
        ):
            self.fields['use_invite_token'].disabled = True

    @property
    def group(self):
        """This is for `FormAttachableMixin` to get passed the group as a target for
        uploading files. Only works after the group has been created however."""
        return self.instance if self.instance.pk else None

    def clean(self):
        if not self.cleaned_data.get('name', None):
            name = self.get_cleaned_name_from_other_languages()
            if name:
                self.cleaned_data['name'] = name
                self.data['name'] = name
                if 'name' in self.errors:
                    del self.errors['name']
        return super(CosinnusBaseGroupForm, self).clean()

    def clean_video(self):
        data = self.cleaned_data['video']
        if data:
            parsed_video = self.instance.get_video_properties(video=data)
            if not parsed_video or 'error' in parsed_video:
                raise forms.ValidationError(_("This doesn't seem to be a valid Youtube or Vimeo link!"))
        return data

    def clean_sdgs(self):
        if self.cleaned_data['sdgs'] and len(self.cleaned_data) > 0:
            return [int(sdg) for sdg in self.cleaned_data['sdgs']]

    def clean_twitter_username(self):
        """check username and enforce '@'"""
        data = self.cleaned_data['twitter_username']
        if data:
            data = data.strip()
            if not TWITTER_USERNAME_VALID_RE.match(data):
                raise forms.ValidationError(_("This doesn't seem to be a Twitter username!"))
            data = '@' + data.replace('@', '')
        return data

    def clean_twitter_widget_id(self):
        """Accept Widget-id (example: 744907261810618721) or embed-code (HTML)
        always returns empty or a numeral like 744907261810618721"""
        data = self.cleaned_data['twitter_widget_id']
        if data:
            data = data.strip()
            if _is_number(data):
                return data
            match = TWITTER_WIDGET_EMBED_ID_RE.search(data)
            if match and _is_number(match.group(1)):
                return match.group(1)
            raise forms.ValidationError(_("This doesn't seem to be a valid widget ID or embed HTML code from Twitter!"))
        return data

    def clean_flickr_url(self):
        data = self.cleaned_data['flickr_url']
        if data:
            parsed_flickr = self.instance.get_flickr_properties(flickr=data)
            if not parsed_flickr or 'error' in parsed_flickr:
                raise forms.ValidationError(
                    _(
                        'This doesn\'t seem to be a valid Flickr Gallery link! It should be in the form of "https://www.flickr.com/photos/username/sets/1234567890"!'
                    )
                )
        return data

    def save(self, commit=True):
        """Support for m2m-MultipleModelChoiceFields. Saves all selected relations.
        from http://stackoverflow.com/questions/2216974/django-modelform-for-many-to-many-fields"""
        self.instance = super(CosinnusBaseGroupForm, self).save(commit=False)
        # Prepare a 'save_m2m' method for the form,
        old_save_m2m = self.save_m2m

        def save_m2m():
            old_save_m2m()

            new_group_slugs = [new_group.slug for new_group in self.cleaned_data['related_groups']]
            old_related_group_slugs = self.instance.related_groups.all().values_list('slug', flat=True)
            # remove no longer wanted related_groups
            for old_slug in old_related_group_slugs:
                if old_slug not in new_group_slugs:
                    old_group_rel = get_object_or_None(RelatedGroups, to_group=self.instance, from_group__slug=old_slug)
                    old_group_rel.delete()
            # add new related_groups
            user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(self.request.user)
            user_superuser = check_user_superuser(self.request.user)

            # we need to split email and alert here, because
            # emails should check the notification settings normally,
            # but for alerts, we need to check if the user is following the *target group*!
            # (the notification logic for user_wants_alert would always return true on a group object)
            conference_notification_email_pairs = []
            conference_notification_alert_pairs = []

            for related_group in self.cleaned_data['related_groups']:
                # in the context of notifications for each target related group (the groups getting notified),
                # we attach that group as `notification_target_group` property to our origin group that
                # was created (this) to hand over to the notifications receiver. we use a copied instance so we can
                # attach different origin groups, becase the notifications will be evaluated *after* this loop
                context_origin_group = copy(self.instance)

                # non-superuser users can only tag groups they are in
                if not user_superuser and related_group.id not in user_group_ids:
                    continue
                # only create group rel if it didn't exist
                existing_group_rel = get_object_or_None(
                    RelatedGroups, to_group=context_origin_group, from_group=related_group
                )
                if not existing_group_rel:
                    # create a new related group link
                    RelatedGroups.objects.create(to_group=context_origin_group, from_group=related_group)
                    # if the current group is a conference, and the related group is a society or project,
                    # the conference will be reflected into the group, so we send a notification
                    non_conference_group_types = [
                        get_cosinnus_group_model().TYPE_PROJECT,
                        get_cosinnus_group_model().TYPE_SOCIETY,
                    ]
                    if context_origin_group.group_is_conference and related_group.type in non_conference_group_types:
                        audience_group_members_except_creator = [
                            member for member in related_group.actual_members if member.id != self.request.user.id
                        ]
                        audience_group_followers_except_creator_ids = [
                            pk for pk in related_group.get_followed_user_ids() if pk not in [self.request.user.id]
                        ]
                        audience_group_followers_except_creator = get_user_model().objects.filter(
                            id__in=audience_group_followers_except_creator_ids
                        )
                        # HERE: we should send alerts only for followers of the target group,
                        #    but send the email notification for members, independent of following
                        # set the target group for the notification onto the group instance
                        setattr(context_origin_group, 'notification_target_group', related_group)
                        conference_notification_email_pairs.append(
                            (context_origin_group, audience_group_members_except_creator)
                        )
                        conference_notification_alert_pairs.append(
                            (context_origin_group, audience_group_followers_except_creator)
                        )

            # send notifications in a session to avoid duplicate messages to any user
            session_notification_id = uuid1().int
            # send email/alert in a different session each
            session_alert_id = uuid1().int
            # send notifications in a session to avoid duplicate messages to any user
            for i, pair in enumerate(conference_notification_email_pairs):
                cosinnus_notifications.conference_created_in_group.send(
                    sender=self,
                    user=self.request.user,
                    obj=pair[0],
                    audience=pair[1],
                    session_id=session_notification_id,
                    end_session=bool(i == len(conference_notification_email_pairs) - 1),
                )
            # send email/alert in a different session each
            for i, pair in enumerate(conference_notification_alert_pairs):
                cosinnus_notifications.conference_created_in_group_alert.send(
                    sender=self,
                    user=self.request.user,
                    obj=pair[0],
                    audience=pair[1],
                    session_id=session_alert_id,
                    end_session=bool(i == len(conference_notification_alert_pairs) - 1),
                )

        self.save_m2m = save_m2m
        if commit:
            self.instance.save()
            # we skip the call to `save_m2m` here, because the django-multiform `MultiModelForm` already calls it!
            # self.save_m2m()

            # since we didn't call super().save with commit=True, call this for certain forms to catch up
            if hasattr(self, 'post_uncommitted_save'):
                self.post_uncommitted_save(self.instance)
        return self.instance


class _CosinnusProjectForm(CleanAppSettingsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):
    """Specific form implementation for CosinnusProject objects (used through `registration.group_models`)"""

    membership_mode = forms.ChoiceField(choices=CosinnusProject.MEMBERSHIP_MODE_CHOICES, required=False)

    dynamic_forms_setting = 'COSINNUS_PROJECT_ADDITIONAL_FORMS'

    class Meta(object):
        fields = CosinnusBaseGroupForm.Meta.fields + ['parent', 'video_conference_type']
        model = CosinnusProject

    def __init__(self, instance, *args, **kwargs):
        super(_CosinnusProjectForm, self).__init__(instance=instance, *args, **kwargs)
        # choosable groups are only the ones the user is a member of, and never the forum
        user_group_ids = list(CosinnusSociety.objects.get_for_user_pks(self.request.user))
        # choosable are also conferences the user is an admin of
        user_conference_ids = list(CosinnusConference.objects.get_for_user_group_admin_pks(self.request.user))

        conference_and_group_types = [
            get_cosinnus_group_model().TYPE_SOCIETY,
            get_cosinnus_group_model().TYPE_CONFERENCE,
        ]
        groups_and_conferences = get_cosinnus_group_model().objects.filter(type__in=conference_and_group_types)
        qs = groups_and_conferences.filter(
            portal=CosinnusPortal.get_current(), is_active=True, id__in=user_group_ids + user_conference_ids
        )

        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        if forum_slug:
            qs = qs.exclude(slug=forum_slug)
        self.fields['parent'].queryset = qs


class _CosinnusSocietyForm(CleanAppSettingsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):
    """Specific form implementation for CosinnusSociety objects (used through `registration.group_models`)"""

    membership_mode = forms.ChoiceField(choices=CosinnusSociety.MEMBERSHIP_MODE_CHOICES, required=False)

    dynamic_forms_setting = 'COSINNUS_GROUP_ADDITIONAL_FORMS'

    class Meta(object):
        fields = CosinnusBaseGroupForm.Meta.fields + [
            'video_conference_type',
        ]
        model = CosinnusSociety


class _CosinnusConferenceForm(
    CleanAppSettingsMixin, CleanFromToDateFieldsMixin, AsssignPortalMixin, CosinnusBaseGroupForm
):
    """Specific form implementation for CosinnusConference objects (used through `registration.group_models`)"""

    from_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='00:00'))
    to_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='23:59'))
    membership_mode = forms.ChoiceField(
        initial=(
            CosinnusConference.MEMBERSHIP_MODE_APPLICATION
            if settings.COSINNUS_CONFERENCES_USE_APPLICATIONS_CHOICE_DEFAULT
            else CosinnusConference.MEMBERSHIP_MODE_REQUEST
        ),
        choices=CosinnusConference.MEMBERSHIP_MODE_CHOICES,
        required=False,
    )

    dynamic_forms_setting = 'COSINNUS_CONFERENCE_ADDITIONAL_FORMS'

    class Meta(object):
        fields = CosinnusBaseGroupForm.Meta.fields + [
            'conference_theme_color',
            'from_date',
            'to_date',
        ]
        model = CosinnusConference


class MembershipForm(GroupKwargModelFormMixin, forms.ModelForm):
    class Meta(object):
        fields = (
            'user',
            'status',
        )
        model = CosinnusGroupMembership

    def __init__(self, *args, **kwargs):
        user_qs = kwargs.pop('user_qs')
        super(MembershipForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = user_qs
        self.initial.setdefault('status', MEMBERSHIP_MEMBER)

    def save(self, *args, **kwargs):
        obj = super(MembershipForm, self).save(commit=False)
        obj.group = self.group
        obj.save()
        return obj


class MultiSelectForm(forms.Form):
    """The form to select items in a select2 field"""

    select_field = ''

    def __init__(self, *args, **kwargs):
        super(MultiSelectForm, self).__init__(*args, **kwargs)
        self.init_items(**kwargs)

    def init_items(self, **kwargs):
        # Retrieve the attached objects ids to select them in the update view
        items, item_list, results = [], [], []
        initial = kwargs.get('initial', {}).get(self.select_field, None)
        use_ids = False

        if initial:
            item_list = initial.split(', ')
            # delete the initial data or our select2 field initials will be overwritten by django
            if self.select_field in kwargs['initial']:
                del kwargs['initial'][self.select_field]
            if self.select_field in self.initial:
                del self.initial[self.select_field]
        elif 'data' in kwargs and kwargs['data'].getlist(self.select_field):
            item_list = kwargs['data'].getlist(self.select_field)
            use_ids = True

        if item_list:
            ids = self.fields[self.select_field].get_ids_for_value(item_list, intify=use_ids)
            ids_type = self.select_field[:-1]
            queryset = self.get_queryset()
            if use_ids:
                items = queryset.filter(id__in=ids[ids_type])
            else:
                items = queryset.filter(username__in=ids[ids_type])
            results = self.get_select2_pills(items, text_only=False)

        # we need to cheat our way around select2's annoying way of clearing initial data fields
        self.fields[self.select_field].choices = results
        self.fields[self.select_field].initial = [key for key, __ in results]
        self.fields[self.select_field].widget.options['ajax']['url'] = self.get_ajax_url()
        self.initial[self.select_field] = self.fields[self.select_field].initial

    def get_queryset(self):
        return NotImplementedError

    def get_select2_pills(self, items, text_only=False):
        return NotImplementedError

    def get_ajax_url(self):
        return NotImplementedError


class MultiUserSelectForm(MultiSelectForm):
    """The form to select users in a select2 field"""

    select_field = 'users'

    # specify help_text only to avoid the possible default 'Enter text to search.' of ajax_select v1.2.5
    users = UserSelect2MultipleChoiceField(label=_('Users'), data_url='/stub/')

    class Meta(object):
        fields = ('users',)

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group')
        self.user = kwargs.pop('user', None)
        super(MultiUserSelectForm, self).__init__(*args, **kwargs)

    def get_queryset(self):
        include_uids = CosinnusPortal.get_current().members
        exclude_uids = self.group.members
        users = filter_active_users(get_user_model().objects.filter(id__in=include_uids).exclude(id__in=exclude_uids))
        # support for user blocking, filter out all audience members that have the sending user blocked
        if settings.COSINNUS_ENABLE_USER_BLOCK and self.user:
            blocked_user_ids = UserBlock.get_blocking_user_ids_for_user(self.user)
            if blocked_user_ids:
                users = users.exclude(id__in=blocked_user_ids)
        return users

    def get_select2_pills(self, items, text_only=False):
        return get_user_select2_pills(items, text_only=text_only)

    def get_ajax_url(self):
        if isinstance(self.group, CosinnusOrganization):
            return reverse('cosinnus:organization-member-invite-select2', kwargs={'organization': self.group.slug})
        return group_aware_reverse('cosinnus:group-member-invite-select2', kwargs={'group': self.group})


class MultiGroupSelectForm(MultiSelectForm):
    select_field = 'groups'

    # specify help_text only to avoid the possible default 'Enter text to search.' of ajax_select v1.2.5
    groups = GroupSelect2MultipleChoiceField(label=_('Groups'), data_url='/stub/')

    class Meta(object):
        fields = ('groups',)

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        include_uids = CosinnusPortal.get_current().groups.values_list('id', flat=True)
        queryset = get_cosinnus_group_model().objects.filter(id__in=include_uids)
        if self.group and isinstance(self.group, CosinnusOrganization):
            exclude_uids = self.organization.groups.values_list('id', flat=True)
            queryset = queryset.exclude(id__in=exclude_uids)
        return queryset

    def get_select2_pills(self, items, text_only=False):
        return get_group_select2_pills(items, text_only=text_only)

    def get_ajax_url(self):
        if self.group:
            if isinstance(self.group, CosinnusOrganization):
                return reverse('cosinnus:organization-group-invite-select2', kwargs={'organization': self.group.slug})
            else:
                return group_aware_reverse('cosinnus:group-invite-select2', kwargs={'group': self.group.slug})
        return ''


class CosinnusLocationForm(forms.ModelForm):
    class Meta(object):
        model = CosinnusLocation
        fields = (
            'group',
            'location',
            'location_lat',
            'location_lon',
        )
        widgets = {
            'location_lat': forms.HiddenInput(),
            'location_lon': forms.HiddenInput(),
        }


class CosinnusGroupGalleryImageForm(forms.ModelForm):
    class Meta(object):
        model = CosinnusGroupGalleryImage
        fields = (
            'group',
            'image',
        )


class CosinnusGroupCallToActionButtonForm(forms.ModelForm):
    url = forms.URLField(widget=forms.TextInput, required=False)

    class Meta(object):
        model = CosinnusGroupCallToActionButton
        fields = (
            'group',
            'label',
            'url',
        )


class CosinusWorkshopParticipantCSVImportForm(forms.Form):
    participants = forms.FileField()

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)

    def clean_participants(self):
        csv_file = self.cleaned_data['participants']
        reader = self.process_csv(csv_file)
        header = next(reader, None)
        cleaned_header = self.clean_row_data(header)
        data = self.process_and_validate_data(reader)

        return {'header_original': cleaned_header, 'data': data}

    def process_and_validate_data(self, reader):
        data = []
        usernames = []

        for row in reader:
            cleaned_row = self.clean_row_data(row)
            username = cleaned_row[0]
            first_name = cleaned_row[1]
            if not username:
                raise forms.ValidationError(_('Please always provide a username'))
            if not first_name:
                raise forms.ValidationError(_('Please always provide a first name'))
            if ' ' in username:
                raise forms.ValidationError(_("Please remove the whitespace from '{}'").format(username))
            if username not in usernames:
                usernames.append(username)
            else:
                raise forms.ValidationError(
                    _(
                        "Names must be unique. You added '{}' more" ' then once to your CSV. Please change the name.'
                    ).format(username)
                )
            data.append(self.clean_row_data(cleaned_row))

        return data

    def process_csv(self, csv_file):
        try:
            raw_file = csv_file.read()
            encoding = chardet.detect(raw_file)['encoding']
            file = raw_file.decode(encoding)
            io_string = io.StringIO(file)
            dialect = csv.Sniffer().sniff(io_string.read(102400000), delimiters=';,')
            io_string.seek(0)
            reader = csv.reader(io_string, dialect)
            return reader
        except UnicodeDecodeError:
            raise forms.ValidationError(_('This is not a valid CSV File'))
        except csv.Error:
            raise forms.ValidationError(_("CSV could not be parsed. Please use ',' or ';' as delimiter."))

    def clean_row_data(self, row):
        cleaned_row = []
        for entry in row:
            cleaned_row.append(entry.strip())
        return cleaned_row


class GroupContactForm(forms.Form):
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)
    captcha = CaptchaField()
