# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from builtins import object
import re
import csv
import io

from django import forms
from django.forms.widgets import SelectMultiple
from django_select2.widgets import Select2MultipleWidget
from django.utils.translation import ugettext_lazy as _

from awesome_avatar import forms as avatar_forms

from cosinnus.forms.mixins import AdditionalFormsMixin
from cosinnus_organization.models import CosinnusOrganization
from cosinnus.models.group import (CosinnusGroupMembership,
                                   CosinnusPortal,
    CosinnusLocation, RelatedGroups, CosinnusGroupGalleryImage,
    CosinnusGroupCallToActionButton)
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.core.registries.apps import app_registry
from cosinnus.conf import settings
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from django_select2.fields import HeavyModelSelect2MultipleChoiceField
from cosinnus.utils.group import get_cosinnus_group_model
from django.urls import reverse
from cosinnus.views.facebook_integration import FacebookIntegrationGroupFormMixin
from cosinnus.utils.lanugages import MultiLanguageFieldValidationFormMixin
from cosinnus.fields import UserSelect2MultipleChoiceField
from django.contrib.auth import get_user_model
from cosinnus.utils.user import get_user_select2_pills, filter_active_users
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.templatetags.cosinnus_tags import is_superuser
from django.core.exceptions import ObjectDoesNotExist
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.group import SDG_CHOICES
from cosinnus.forms.managed_tags import ManagedTagFormMixin

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
        
        deactivated_apps = [option_app for option_app in deactivatable_apps if not option_app in active_apps]
        return ','.join(deactivated_apps)
    
    def clean_microsite_public_apps(self):
        deactivatable_apps = app_registry.get_deactivatable_apps()
        # public apps are checked
        public_apps = self.data.getlist('microsite_public_apps')
        # only accept existing, deactivatable apps
        public_apps = [option_app for option_app in deactivatable_apps if option_app in public_apps]
        return ','.join(public_apps) if public_apps else '<all_deselected>'
    

class AsssignPortalMixin(object):
    """ Assign current portal on save when created """
    
    def save(self, **kwargs):
        if self.instance.pk is None:  
            self.instance.portal = CosinnusPortal.get_current()
        return super(AsssignPortalMixin, self).save(**kwargs)


class CosinnusBaseGroupForm(FacebookIntegrationGroupFormMixin, MultiLanguageFieldValidationFormMixin, 
                ManagedTagFormMixin, AdditionalFormsMixin, forms.ModelForm):
    
    avatar = avatar_forms.AvatarField(required=getattr(settings, 'COSINNUS_GROUP_AVATAR_REQUIRED', False), disable_preview=True)
    website = forms.URLField(widget=forms.TextInput, required=False)
    # we want a textarea without character limit here so HTML can be pasted (will be cleaned)
    twitter_widget_id = forms.CharField(widget=forms.Textarea, required=False)
    sdgs = forms.MultipleChoiceField(choices=SDG_CHOICES, required=False)
    
    related_groups = forms.ModelMultipleChoiceField(queryset=get_cosinnus_group_model().objects.none())
    
    if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS:
        managed_tag_field = forms.CharField(required=False)
    
    class Meta(object):
        fields = ['name', 'public', 'description', 'description_long', 'contact_info', 'sdgs',
                        'avatar', 'wallpaper', 'website', 'video', 'twitter_username',
                         'twitter_widget_id', 'flickr_url', 'deactivated_apps', 'microsite_public_apps',
                         'call_to_action_active', 'call_to_action_title', 'call_to_action_description',
                         'conference_theme_color'] \
                        + getattr(settings, 'COSINNUS_GROUP_ADDITIONAL_FORM_FIELDS', []) \
                        + (['facebook_group_id', 'facebook_page_id',] if settings.COSINNUS_FACEBOOK_INTEGRATION_ENABLED else []) \
                        + (['embedded_dashboard_html',] if settings.COSINNUS_GROUP_DASHBOARD_EMBED_HTML_FIELD_ENABLED else []) \
                        + (['managed_tag_field',] if (settings.COSINNUS_MANAGED_TAGS_ENABLED \
                                                      and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS) else [])

    def __init__(self, instance, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(CosinnusBaseGroupForm, self).__init__(instance=instance, *args, **kwargs)
            
        self.fields['related_groups'] = HeavyModelSelect2MultipleChoiceField(
                 required=False, 
                 data_url=reverse('cosinnus:select2:groups') + ('?except='+str(instance.pk) if instance else ''),
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
                
        # for conference groups, add additional form fields
        if instance is None or not instance.pk or not instance.group_is_conference:
            del self.fields['conference_theme_color']
    
    
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
                raise forms.ValidationError(_('This doesn\'t seem to be a valid Youtube or Vimeo link!'))
        return data

    def clean_sdgs(self):
        if self.cleaned_data['sdgs'] and len(self.cleaned_data) > 0:
            return [int(sdg) for sdg in self.cleaned_data['sdgs']]
    
    def clean_twitter_username(self):
        """ check username and enforce '@' """
        data = self.cleaned_data['twitter_username']
        if data:
            data = data.strip()
            if not TWITTER_USERNAME_VALID_RE.match(data):
                raise forms.ValidationError(_('This doesn\'t seem to be a Twitter username!'))
            data = '@' + data.replace('@', '')
        return data
    
    def clean_twitter_widget_id(self):
        """ Accept Widget-id (example: 744907261810618721) or embed-code (HTML)
            always returns empty or a numeral like 744907261810618721 """
        data = self.cleaned_data['twitter_widget_id']
        if data:
            data = data.strip()
            if _is_number(data):
                return data
            match = TWITTER_WIDGET_EMBED_ID_RE.search(data)
            if match and _is_number(match.group(1)):
                return match.group(1)
            raise forms.ValidationError(_('This doesn\'t seem to be a valid widget ID or embed HTML code from Twitter!'))
        return data
    
    def clean_flickr_url(self):
        data = self.cleaned_data['flickr_url']
        if data:
            parsed_flickr = self.instance.get_flickr_properties(flickr=data)
            if not parsed_flickr or 'error' in parsed_flickr:
                raise forms.ValidationError(_('This doesn\'t seem to be a valid Flickr Gallery link! It should be in the form of "https://www.flickr.com/photos/username/sets/1234567890"!'))
        return data
    
    def save(self, commit=True):
        """ Support for m2m-MultipleModelChoiceFields. Saves all selected relations.
            from http://stackoverflow.com/questions/2216974/django-modelform-for-many-to-many-fields """
        self.instance = super(CosinnusBaseGroupForm, self).save(commit=False)
        # Prepare a 'save_m2m' method for the form,
        old_save_m2m = self.save_m2m
        def save_m2m():
            old_save_m2m()
            self.instance.related_groups.clear()
            for related_group in self.cleaned_data['related_groups']:
                #self.instance.related_groups.add(related_group)
                # add() is disabled for a self-referential models, so we create an instance of the through-model
                RelatedGroups.objects.get_or_create(to_group=self.instance, from_group=related_group) 
                
        self.save_m2m = save_m2m
        if commit:
            self.instance.save()
            self.save_m2m()
            # since we didn't call super().save with commit=True, call this for certain forms to catch up
            if hasattr(self, 'post_uncommitted_save'):
                self.post_uncommitted_save(self.instance)
        return self.instance
                
                
class _CosinnusProjectForm(CleanAppSettingsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):

    extra_forms_setting = 'COSINNUS_PROJECT_ADDITIONAL_FORMS'

    class Meta(object):
        fields = CosinnusBaseGroupForm.Meta.fields + ['parent',]
        model = CosinnusProject
    
    def __init__(self, instance, *args, **kwargs):    
        super(_CosinnusProjectForm, self).__init__(instance=instance, *args, **kwargs)
        # choosable groups are only the ones the user is a member of, and never the forum
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        user_group_ids = CosinnusSociety.objects.get_for_user_pks(self.request.user)
        qs = CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, id__in=user_group_ids)
        if forum_slug:
            qs = qs.exclude(slug=forum_slug)
        self.fields['parent'].queryset = qs


class _CosinnusSocietyForm(CleanAppSettingsMixin, AsssignPortalMixin, CosinnusBaseGroupForm):

    extra_forms_setting = 'COSINNUS_GROUP_ADDITIONAL_FORMS'

    class Meta(object):
        fields = CosinnusBaseGroupForm.Meta.fields
        model = CosinnusSociety
        

class MembershipForm(GroupKwargModelFormMixin, forms.ModelForm):

    class Meta(object):
        fields = ('user', 'status',)
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
    

class MultiUserSelectForm(forms.Form):
    """ The form to select users in a select2 field """
    
    # specify help_text only to avoid the possible default 'Enter text to search.' of ajax_select v1.2.5
    users = UserSelect2MultipleChoiceField(label=_("Users"), data_url='/stub/')
    
    class Meta(object):
        fields = ('users',)
        
    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group')
        super(MultiUserSelectForm, self).__init__(*args, **kwargs)
        
        include_uids = CosinnusPortal.get_current().members
        exclude_uids = self.group.members
        user_qs = filter_active_users(get_user_model().objects.filter(id__in=include_uids).exclude(id__in=exclude_uids))
        
        # retrieve the attached objects ids to select them in the update view
        users = []
        initial_users = kwargs.get('initial', {}).get('users', None)
        preresults = []
        use_ids = False
        user_list = []
        
        if initial_users:
            user_list = initial_users.split(', ')
            # delete the initial data or our select2 field initials will be overwritten by django
            if 'users' in kwargs['initial']:
                del kwargs['initial']['users']
            if 'users' in self.initial:
                del self.initial['users']
        elif 'data' in kwargs and kwargs['data'].getlist('users'):
            user_list = kwargs['data'].getlist('users')
            use_ids = True
            
        if user_list:
            user_tokens, __ = self.fields['users'].get_user_and_group_ids_for_value(user_list, intify=use_ids)
            if use_ids:
                users = user_qs.filter(id__in=user_tokens)
            else:
                users = user_qs.filter(username__in=user_tokens)
            
            preresults = get_user_select2_pills(users, text_only=False)
            
        # we need to cheat our way around select2's annoying way of clearing initial data fields
        self.fields['users'].choices = preresults
        self.fields['users'].initial = [key for key,__ in preresults]
        self.fields['users'].widget.options['ajax']['url'] = self.get_ajax_url()
        self.initial['users'] = self.fields['users'].initial

    def get_ajax_url(self):
        if isinstance(self.group, CosinnusOrganization):
            return reverse('cosinnus:organization-member-invite-select2', kwargs={'organization': self.group.slug})
        return group_aware_reverse('cosinnus:group-member-invite-select2', kwargs={'group': self.group})


class CosinnusLocationForm(forms.ModelForm):

    class Meta(object):
        model = CosinnusLocation
        fields = ('group', 'location', 'location_lat', 'location_lon', )
        widgets = {
            'location_lat': forms.HiddenInput(),
            'location_lon': forms.HiddenInput(),
        }


class CosinnusGroupGalleryImageForm(forms.ModelForm):

    class Meta(object):
        model = CosinnusGroupGalleryImage
        fields = ('group', 'image', )


class CosinnusGroupCallToActionButtonForm(forms.ModelForm):
    
    url = forms.URLField(widget=forms.TextInput, required=False)
    
    class Meta(object):
        model = CosinnusGroupCallToActionButton
        fields = ('group', 'label', 'url', )


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

        group_header = self.process_and_validate_header(cleaned_header)
        data = self.process_and_validate_data(reader)

        return {
            'header_original': cleaned_header,
            'header': group_header,
            'data': data
        }

    def process_and_validate_data(self, reader):
        data = []
        workshop_usernames = []

        for row in reader:
            cleaned_row = self.clean_row_data(row)
            workshop_username = cleaned_row[0]
            if ' ' in workshop_username:
                raise forms.ValidationError(_("Please remove the whitespace from '{}'").format(workshop_username))
            if workshop_username not in workshop_usernames:
                workshop_usernames.append(workshop_username)
            else:
                raise forms.ValidationError(_("Names must be unique. You added '{}' more"
                                              " then once to your CSV. Please change the name.").format(workshop_username))
            data.append(self.clean_row_data(cleaned_row))

        return data

    def process_and_validate_header(self, header):
        group_header = ['', '', '']

        for slug in header[3:]:
                try:
                    group = CosinnusGroup.objects.get(parent=self.group,
                                                      portal=self.group.portal,
                                                      type=CosinnusGroup.TYPE_PROJECT,
                                                      slug=slug.lower())
                    group_header.append(group)
                except ObjectDoesNotExist:
                    raise forms.ValidationError(_("Can't find workshop with slug '{}'").format(slug))
        return group_header

    def process_csv(self, csv_file):
        try:
            file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file)
            dialect = csv.Sniffer().sniff(io_string.read(1024), delimiters=";,")
            io_string.seek(0)
            reader = csv.reader(io_string, dialect)
            return reader
        except UnicodeDecodeError:
            raise forms.ValidationError(_("This is not a valid CSV File"))
        except csv.Error:
            raise forms.ValidationError(_("CSV could not be parsed. Please use ',' or ';' as delimiter."))


    def clean_row_data(self, row):
        cleaned_row = []
        for entry in row:
            cleaned_row.append(entry.strip())
        return cleaned_row
