# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
import pytz
import logging
from builtins import object
from builtins import zip
from copy import deepcopy

import six
from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ValidationError, \
    PermissionDenied
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http.response import Http404, HttpResponseNotAllowed, \
    HttpResponseBadRequest
from django.shortcuts import redirect, get_object_or_404
from django.template.defaultfilters import linebreaksbr
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy, NoReverseMatch
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.generic import (CreateView, DeleteView, DetailView,
                                  ListView, UpdateView, TemplateView)
from django.views.generic.base import View
from django.views.generic.edit import FormView
from django_select2.views import NO_ERR_RESP, Select2View
from extra_views import (CreateWithInlinesView, InlineFormSetFactory,
                         UpdateWithInlinesView)
from multiform.forms import InvalidArgument

from cosinnus import cosinnus_notifications
from cosinnus.api.serializers.group import GroupSimpleSerializer
from cosinnus.api.serializers.user import UserSerializer
from cosinnus.core import signals
from cosinnus.core.decorators.views import membership_required, redirect_to_403, \
    dispatch_group_access, get_group_for_request, redirect_to_not_logged_in,\
    require_read_access
from cosinnus.core.registries import app_registry
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.forms.group import CosinusWorkshopParticipantCSVImportForm, MembershipForm, CosinnusLocationForm, \
    CosinnusGroupGalleryImageForm, CosinnusGroupCallToActionButtonForm, MultiUserSelectForm, MultiGroupSelectForm
from cosinnus.forms.tagged import get_form
from cosinnus.models import group  # circular import
from cosinnus.models.group import (CosinnusGroup, CosinnusGroupInviteToken, CosinnusGroupMembership,
                                   CosinnusPortal, CosinnusLocation,
                                   CosinnusGroupGalleryImage, CosinnusGroupCallToActionButton,
                                   CosinnusUnregisterdUserGroupInvite)
from cosinnus.models.group_extra import CosinnusSociety, \
    ensure_group_type, CosinnusConference
from cosinnus.models.membership import MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING, MEMBERSHIP_ADMIN, \
    MEMBERSHIP_INVITED_PENDING, MEMBER_STATUS, MembershipClassMixin
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME
from cosinnus.models.profile import UserProfile
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject, BaseTaggableObjectReflection
from cosinnus.search_indexes import CosinnusProjectIndex, CosinnusSocietyIndex
from cosinnus.templatetags.cosinnus_tags import is_superuser, full_name
from cosinnus.utils.compat import atomic
from cosinnus.utils.functions import resolve_class
from cosinnus.utils.group import get_group_query_filter_for_search_terms, get_cosinnus_group_model, prioritize_suggestions_output
from cosinnus.utils.permissions import check_ug_admin, check_user_superuser, \
    check_object_read_access, check_ug_membership, check_object_write_access, \
    check_user_can_see_user, check_user_can_create_conferences
from cosinnus.utils.urls import get_non_cms_root_url, redirect_next_or
from cosinnus.utils.urls import redirect_with_next, group_aware_reverse
from cosinnus.utils.user import create_base_user, filter_active_users, get_user_select2_pills, \
    get_user_query_filter_for_search_terms, get_user_by_email_safe, get_group_select2_pills
from cosinnus.views.microsite import GroupMicrositeView
from cosinnus.views.mixins.ajax import (DetailAjaxableResponseMixin,
                                        AjaxableFormMixin, ListAjaxableResponseMixin)
from cosinnus.views.mixins.avatar import AvatarFormMixin
from cosinnus.views.mixins.group import GroupIsConferenceMixin,\
    RequireVerifiedUserMixin
from cosinnus.views.mixins.group import RequireAdminMixin, RequireReadMixin, \
    RequireLoggedInMixin, EndlessPaginationMixin, RequireWriteMixin
from cosinnus.views.mixins.reflected_objects import ReflectedObjectSelectMixin
from cosinnus.views.mixins.user import UserFormKwargsMixin
from cosinnus.views.profile import delete_userprofile
from cosinnus.views.widget import GroupDashboard
from cosinnus_organization.forms import MultiOrganizationSelectForm
from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationGroup
from cosinnus_organization.utils import get_organization_select2_pills
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.views.attached_object import AttachableViewMixin
from cosinnus.core.middleware import inactive_logout_middleware
from cosinnus.forms.conference import CosinnusConferenceSettingsMultiForm


logger = logging.getLogger('cosinnus')


class SamePortalGroupMixin(object):

    def get_queryset(self):
        """
        Filter the queryset for this portal only!
        """
        return super(SamePortalGroupMixin, self).get_queryset().filter(portal=CosinnusPortal.get_current())


class CosinnusLocationInlineFormset(InlineFormSetFactory):
    factory_kwargs = {
        'extra': 5,
        'max_num': 5,
    }    
    form_class = CosinnusLocationForm
    model = CosinnusLocation


class CosinnusGroupGalleryImageInlineFormset(InlineFormSetFactory):
    factory_kwargs = {
        'extra': 6,
        'max_num': 6,
    }
    form_class = CosinnusGroupGalleryImageForm
    model = CosinnusGroupGalleryImage


class CosinnusGroupCallToActionButtonInlineFormset(InlineFormSetFactory):
    factory_kwargs = {
        'extra': 10,
        'max_num': 10,
    }
    form_class = CosinnusGroupCallToActionButtonForm
    model = CosinnusGroupCallToActionButton


class CosinnusGroupFormMixin(object):
    
    model = CosinnusGroup
    # we can define additional inline formsets in settings.COSINNUS_GROUP_ADDITIONAL_INLINE_FORMSETS
    inlines = [CosinnusLocationInlineFormset, CosinnusGroupGalleryImageInlineFormset, CosinnusGroupCallToActionButtonInlineFormset] \
                + ([resolve_class(class_path) for class_path in settings.COSINNUS_GROUP_ADDITIONAL_INLINE_FORMSETS] \
                    if getattr(settings, 'COSINNUS_GROUP_ADDITIONAL_INLINE_FORMSETS', []) else [])
    template_name = 'cosinnus/group/group_form.html'
    
    def get_form_kwargs(self):
        kwargs = super(CosinnusGroupFormMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def dispatch(self, *args, **kwargs):
        """ Find out which type of CosinnusGroup (project/society), we're dealing with here. """
        group_url_key = self.request.path.split('/')[1]
        form_class = group_model_registry.get_form(group_url_key, None)
        model_class = group_model_registry.get(group_url_key, None)
        if not form_class:
            form_class = group_model_registry.get_form_by_plural_key(group_url_key, None)
            model_class = group_model_registry.get_by_plural_key(group_url_key, None)
        self.group_model_class = model_class
        self.group_form_class = form_class
        
        # special check, if group/project creation is limited to admins, deny regular users creating groups/projects
        if getattr(settings, 'COSINNUS_LIMIT_PROJECT_AND_GROUP_CREATION_TO_ADMINS', False) \
                and not check_user_superuser(self.request.user) and self.form_view == 'add':
            messages.warning(self.request, _('Sorry, only portal administrators can create projects and groups!'))
            return redirect(reverse('cosinnus:portal-admin-list'))
        
        society_forbidden = self.form_view == 'add' and model_class == CosinnusSociety and \
                        not getattr(settings, 'COSINNUS_USERS_CAN_CREATE_GROUPS', False)
        conference_forbidden = self.form_view == 'add' and model_class == CosinnusConference and \
                            not getattr(settings, 'COSINNUS_USERS_CAN_CREATE_CONFERENCES', False)
        # check if user is of a managed tag that would allow him to create a conference
        if conference_forbidden:
            conference_forbidden = not check_user_can_create_conferences(self.request.user)
            
        # special check: only portal admins can create groups/conferences
        if society_forbidden or conference_forbidden:
            if not check_user_superuser(self.request.user):
                if getattr(settings, 'COSINNUS_CUSTOM_PREMIUM_PAGE_ENABLED', False):
                    redirect_url = reverse('cosinnus:premium-info-page')
                else:
                    messages.warning(self.request, model_class.get_trans().MESSAGE_ONLY_ADMINS_MAY_CREATE)
                    redirect_url = reverse('cosinnus:portal-admin-list')
                return redirect(redirect_url) 
        
        return super(CosinnusGroupFormMixin, self).dispatch(*args, **kwargs)
    
    def get_form_class(self):
        
        class CosinnusGroupForm(get_form(self.group_form_class, attachable=False,
                         extra_forms={'conference_settings_assignments': CosinnusConferenceSettingsMultiForm})):
            def dispatch_init_group(self, name, group):
                if name == 'media_tag':
                    return group
                return InvalidArgument
            
            def dispatch_init_user(self, name, user):
                if name == 'media_tag':
                    return user
                return InvalidArgument
            
            def dispatch_init_attached_objects_querysets(self, name, qs):
                if name == 'obj':
                    return qs
                return InvalidArgument

            @property
            def save_attachable(self):
                return self.forms['obj'].save_attachable

        return CosinnusGroupForm
    
    def get_form(self, *args, **kwargs):
        form = super(CosinnusGroupFormMixin, self).get_form(*args, **kwargs)
        # disable the userprofile visibility field and set the initial to its value if its locked
        if settings.COSINNUS_CONFERENCES_PUBLIC_SETTING_LOCKED is not None:
            field = form.forms['obj'].fields['public']
            field.disabled = True
            field.required = False
        return form
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusGroupFormMixin, self).get_context_data(**kwargs)
        deactivated_apps = self.object.get_deactivated_apps() if self.object else []
        microsite_public_apps = self.object.get_microsite_public_apps() if self.object else settings.COSINNUS_MICROSITE_DEFAULT_PUBLIC_APPS
        
        deactivated_app_selection = []
        microsite_public_apps_selection = []
        
        for app_name in app_registry: # eg 'cosinnus_todo'
            # label for the checkbox is the app identifier translation
            app = app_name.split('_')[-1] # eg 'todo'
            # filter for cosinnus app being deactivatable (and not group-only if this is not a group)
            if app_registry.is_deactivatable(app_name):
                if not self.object:
                    app_is_active = app_registry.is_active_by_default(app_name)
                else:
                    app_is_active = not self.object.deactivated_apps or app_name not in deactivated_apps
                    
                app_not_activatable = (self.group_model_class.GROUP_MODEL_TYPE != CosinnusGroup.TYPE_SOCIETY and app_registry.is_activatable_for_groups_only(app_name))
                group_label = app_registry.get_label(app_name)
                if app_name in settings.COSINNUS_GROUP_APPS_WIDGET_SETTING_ONLY:
                    group_label = f'{group_label} ({self.group_model_class.get_trans().DASHBOARD_LABEL})'
                deactivated_app_selection.append({
                    'app_name': app_name,
                    'app': app,
                    'label': group_label,
                    'checked': app_is_active,
                    'app_not_activatable': app_not_activatable,
                })
                app_disabled_for_microsite = app_name in settings.COSINNUS_GROUP_APPS_WIDGETS_MICROSITE_DISABLED
                if app_is_active and not app_not_activatable and not app_disabled_for_microsite:
                    microsite_public_apps_selection.append({
                        'app_name': app_name,
                        'app': app,
                        'label': app_registry.get_label(app_name),
                        'checked': app_name in microsite_public_apps,
                    })
            
        context.update({
            'group_model': self.group_model_class.__name__,
            'group_model_class': self.group_model_class,
            'deactivated_app_selection': deactivated_app_selection,
            'microsite_public_apps_selection': microsite_public_apps_selection,
        })
        return context
    
    def post(self, *args, **kwargs):
        # save deactivated_apps for checking after POSTs
        if hasattr(self, 'group'):
            self._old_deactivated_apps = self.group.get_deactivated_apps()
        else:
            self._old_deactivated_apps = []
        ret = super(CosinnusGroupFormMixin, self).post(*args, **kwargs)
        if self.object:
            new_apps = self.object.get_deactivated_apps()
            
            # check if any group apps were activated or deactivated
            deactivated_apps = [app for app in new_apps if not app in self._old_deactivated_apps]
            activated_apps = [app for app in self._old_deactivated_apps if not app in new_apps]
            if activated_apps:
                signals.group_apps_activated.send(sender=self, group=self.object, apps=activated_apps)
            if deactivated_apps:
                signals.group_apps_deactivated.send(sender=self, group=self.object, apps=deactivated_apps)
        return ret
    
    def forms_valid(self, form, inlines):
        """ We update the haystack index again after the inlineforms have also been saved,
            so that data changed in those forms are reflected in the updated group object """
            
        ret = super(CosinnusGroupFormMixin, self).forms_valid(form, inlines)
        if self.object.type == CosinnusGroup.TYPE_PROJECT:
            group_index = CosinnusProjectIndex()
        else:
            group_index = CosinnusSocietyIndex()
            
        group_index.update_object(self.object)
        signals.group_saved_in_form.send(sender=self, group=self.object, user=self.request.user)
        return ret

    def get_success_url(self):
        # form save chains to participation options form if this is a conference and has applications enabled
        if self.object.group_is_conference and self.object.use_conference_applications:
            redirect_url = group_aware_reverse('cosinnus:conference:participation-management', kwargs={'group': self.object})
        else:
            redirect_url = self.object.get_absolute_url()
        return redirect_next_or(self.request, redirect_url)
    

class GroupMembershipMixin(MembershipClassMixin):
    membership_class = CosinnusGroupMembership
    invite_class = CosinnusUnregisterdUserGroupInvite


class GroupCreateView(CosinnusGroupFormMixin, RequireVerifiedUserMixin, AttachableViewMixin, AvatarFormMixin, AjaxableFormMixin, UserFormKwargsMixin,
                      CreateWithInlinesView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!

    form_view = 'add'
    
    message_success = _('%(team_type)s "%(group)s" was created successfully.')

    @method_decorator(membership_required)
    @atomic
    def dispatch(self, *args, **kwargs):
        return super(GroupCreateView, self).dispatch(*args, **kwargs)
    
    def get_initial(self):
        """ Allow pre-populating managed tags on group creation from the user's profile tags """
        initial = super().get_initial()
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS:
            # check if the user is assigned to any tags, and if so, add their comma-seperated slugs
            assigned_tags = list(self.request.user.cosinnus_profile.get_managed_tags())
            if assigned_tags:
                initial['managed_tag_field'] = ','.join([tag.slug for tag in assigned_tags])
            elif settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG is not None:
                initial['managed_tag_field'] = settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG
        return initial
    
    def forms_valid(self, form, inlines):
        ret = super(GroupCreateView, self).forms_valid(form, inlines)
        membership = CosinnusGroupMembership.objects.create(user=self.request.user,
            group=self.object, status=MEMBERSHIP_ADMIN)
        
        # clear cache and manually refill because race conditions can make the group memberships be cached as empty
        membership._refresh_cache()
        membership.group.update_index()

        # During the initial indexing of the admins property of the user the newly created group is not always included
        # in the threaded query. Forcing a reindex to make sure the user is listed as the admin of the created group.
        if hasattr(self.request.user, 'cosinnus_profile'):
            self.request.user.cosinnus_profile.update_index()

        # send group creation signal, 
        # from here, because in group.save() we don't know the group's creator
        # the audience is empty because this is a moderator-only notification
        cosinnus_notifications.group_created.send(sender=self, user=self.request.user, obj=self.object, audience=[])
        
        # add this project as a reference to the idea it was given as param, if given and enabled
        if settings.COSINNUS_IDEAS_ENABLED and self.request.POST.get('idea_shortid', None) and self.object.type == CosinnusGroup.TYPE_PROJECT:
            from cosinnus.models.idea import CosinnusIdea
            shortid = self.request.POST.get('idea_shortid')
            idea = CosinnusIdea.objects.get_by_shortid(shortid)
            if idea:
                idea.created_groups.add(self.object)
                idea.update_index()
                # send out a notification to followers of this idea except for the new project's creator
                idea_followers_ids = [pk for pk in idea.get_followed_user_ids() if not pk in [self.request.user.id]]
                idea_followers = get_user_model().objects.filter(id__in=idea_followers_ids)
                cosinnus_notifications.project_created_from_idea.send(sender=self, obj=self.object, user=self.request.user, audience=idea_followers)
            else:
                logger.error('Could not attach an idea to a project on project creatiion because the idea was not found!', extra={'idea_shortid': shortid})
        
        # for conferences, always create a default "Workshops" room
        if self.object.group_is_conference:
            CosinnusConferenceRoom.objects.create(
                group=self.object,
                type=CosinnusConferenceRoom.TYPE_WORKSHOPS,
                title="Workshops",
                show_chat=not settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE,
                sort_index=2,
                creator=self.request.user
            )
        
        messages.success(self.request, self.message_success % {'group':self.object.name, 'team_type':self.object._meta.verbose_name})
        return ret
    
    def forms_invalid(self, form, inlines):
        # workaround: on validation errors delete the entered tags
        # because taggit tags that don't exist yet cannot be rendered back properly
        # (during rendering, the then only string is attempted to be rendered as a tag-id and then not found)
        try:
            form.forms['media_tag'].data._mutable = True
            del form.forms['media_tag'].data['media_tag-tags']
        except KeyError:
            pass
        return super(GroupCreateView, self).forms_invalid(form, inlines)

    def get_context_data(self, **kwargs):
        context = super(GroupCreateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Create')
        # if we have 'group=xx' in the GET, add the parent if we are looking at a project
        if 'group' in self.request.GET and 'parent' in kwargs['form'].forms['obj']._meta.fields:
            init_parent = CosinnusGroup.objects.get_cached(slugs=self.request.GET.get('group'))
            kwargs['form'].forms['obj'].initial['parent'] = init_parent
            kwargs['form'].forms['obj'].fields['parent'].initial = init_parent
        return context

    def get_form_kwargs(self):
        kwargs = super(GroupCreateView, self).get_form_kwargs()
        kwargs['group'] = self.object
        return kwargs


class GroupDeleteView(SamePortalGroupMixin, AjaxableFormMixin, RequireAdminMixin, DeleteView):

    model = CosinnusGroup
    slug_url_kwarg = 'group'
    success_url = reverse_lazy('cosinnus:group-list')
    template_name = 'cosinnus/group/group_delete.html'

    @atomic
    def dispatch(self, *args, **kwargs):
        return super(GroupDeleteView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupDeleteView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Delete')
        return context


class GroupDetailView(SamePortalGroupMixin, DetailAjaxableResponseMixin, RequireReadMixin,
                      GroupMembershipMixin, DetailView):

    template_name = 'cosinnus/group/group_detail.html'
    serializer_class = GroupSimpleSerializer
    
    # how many regular users are shown on the page. the rest are omitted unless ?show=all is sent
    default_num_members_shown = 25

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        admin_ids = self.membership_class.objects.get_admins(group=self.group)

        user_is_superuser = check_user_superuser(self.request.user)
        user_is_group_admin = self.request.user.id in admin_ids
        hide_members = settings.COSINNUS_FORUM_HIDE_MEMBER_LIST_FOR_NON_ADMINS and \
                       self.group.is_mass_invite_group and not user_is_superuser and not user_is_group_admin
        context.update({
            'hide_members': hide_members,
        })

        if not hide_members:
            all_member_ids = self.membership_class.objects.get_members(group=self.group)
            pending_ids = self.membership_class.objects.get_pendings(group=self.group)
            invited_pending_ids = self.membership_class.objects.get_invited_pendings(group=self.group)

            member_ids = [id for id in all_member_ids if not id in admin_ids]

            # we DON'T filter for current portal here, as pending join requests can come from
            # users in other portals
            # we also exclude users who have never logged in

            _q = get_user_model().objects.all()
            _q = _q.select_related('cosinnus_profile')
            if not user_is_superuser:
                _q = filter_active_users(_q, filter_guests=False)
            _q = _q.order_by('first_name', 'last_name')

            admins = _q.filter(id__in=admin_ids)
            members = _q.filter(id__in=member_ids)
            pendings = _q.filter(id__in=pending_ids)
            invited = _q.filter(id__in=invited_pending_ids)

            hidden_member_count = 0
            if user_is_superuser:
                user_count = filter_active_users(members, filter_guests=False).count()
            else:
                user_count = members.count() # do not filter again as we did it before higher up
            # for admins: count the inactive users
            inactive_member_count = 0
            if user_is_superuser:
                inactive_member_count = members.count() - user_count
            is_member_of_this_group = self.request.user.pk in admin_ids or self.request.user.pk in member_ids or \
                                      check_user_superuser(self.request.user)

            # for public groups if user not a member of the group, show only public users in widget
            if not self.request.user.is_authenticated:
                visibility_level = BaseTagObject.VISIBILITY_ALL
            elif not is_member_of_this_group:
                visibility_level = BaseTagObject.VISIBILITY_GROUP
            else:
                visibility_level = -1

            if visibility_level != -1:
                # admins are always visible in this view, because a they should be contactable
                members = members.filter(cosinnus_profile__media_tag__visibility__gte=visibility_level)
                pendings = pendings.filter(cosinnus_profile__media_tag__visibility__gte=visibility_level)
                invited = invited.filter(cosinnus_profile__media_tag__visibility__gte=visibility_level)
                # concatenate admins into members, because we might have sorted out a private admin, 
                # and the template iterates only over members to display people
                # members = list(set(chain(members, admins)))
                hidden_member_count = user_count - members.count()

            # add admins to user count now, because they are shown even if hidden visibility
            user_count += admins.count()

            # cut off members list to not let the page explode for groups with tons of members
            if not self.request.GET.get('show', '') == 'all':
                more_user_count = members.count()
                members = members[:self.default_num_members_shown]
                more_user_count -= len(members)
            else:
                more_user_count = 0
            # set admins at the top of the list member
            members = list(admins) + list(members)
            # always include current user in list if member, and at top
            if self.request.user.is_authenticated and check_ug_membership(self.request.user, self.group):
                members = [self.request.user] + [member for member in members if member != self.request.user]

            # collect recruited users
            user = self.request.user
            recruited = self.invite_class.objects.filter(group=self.group)
            if not (check_user_superuser(user) or check_ug_admin(user, self.group)):
                # only admins or group admins may see email adresses they haven't invited themselves
                recruited = recruited.filter(invited_by=user)

            # attach invitation/request date from Membership to user objects
            membership_object_user_ids = [user.id for user in invited] + [user.id for user in pendings]
            membership_objects = self.membership_class.objects.filter(user_id__in=membership_object_user_ids, group=self.group)
            dates_dict = dict(membership_objects.values_list('user_id', 'date'))
            for user in invited:
                setattr(user, 'membership_status_date', dates_dict[user.id])
            for user in pendings:
                setattr(user, 'membership_status_date', dates_dict[user.id])
            invited = sorted(invited, key=lambda u: u.membership_status_date, reverse=True)
            pendings = sorted(pendings, key=lambda u: u.membership_status_date, reverse=True)

            invited_groups = []
            if 'invited_groups' in self.group.settings:
                group_ids = self.group.settings.get('invited_groups')
                invited_groups = CosinnusGroup.objects.filter(id__in=group_ids)

            invite_tokens = []
            if 'invite_token' in self.group.settings:
                token = self.group.settings.get('invite_token', None)
                invite_tokens = token and CosinnusGroupInviteToken.objects.filter(portal=self.group.portal, token__iexact=token) or []

            context.update({
                'admins': admins,
                'members': members,
                'pendings': pendings,
                'invited': invited,
                'recruited': recruited,
                'member_count': user_count,
                'inactive_member_count': inactive_member_count,
                'hidden_user_count': hidden_member_count,
                'more_user_count': more_user_count,
                'member_invite_form': MultiUserSelectForm(group=self.group),
                'group_invite_form': MultiGroupSelectForm(group=self.group),
                'invited_groups': invited_groups,
                'user_is_superuser': user_is_superuser,
                'invite_tokens': invite_tokens,
            })
        return context

class GroupMeetingView(SamePortalGroupMixin, RequireReadMixin, DetailView):

    template_name = 'cosinnus/group/group_meeting.html'
    has_bbb_video = False
    has_fairmeeting_video = False
    
    def dispatch(self, request, *args, **kwargs):
        """ Make sure the group has an active video conference configured. """
        ret = super().dispatch(request, *args, **kwargs)
        if not self.has_bbb_video and not self.has_fairmeeting_video:
            messages.error(request, _('This team does not have a video conference configured.'))
            return redirect_to_403(request, view=self, group=self.group)
        return ret

    def get_object(self, queryset=None):
        return self.group
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.has_bbb_video = settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS and \
            self.group.video_conference_type == self.group.BBB_MEETING
        self.has_fairmeeting_video = CosinnusPortal.get_current().video_conference_server and \
            self.group.video_conference_type == self.group.FAIRMEETING
        meeting_url = None
        recording_prompt_required = False
        if self.has_bbb_video:
            meeting_url = self.group.get_bbb_room_queue_api_url()
            bbb_room = getattr(self.group.media_tag, 'bbb_room')
            recording_prompt_required = bbb_room and bbb_room.is_recorded_meeting or False
        elif self.has_fairmeeting_video:
            meeting_url = f'{CosinnusPortal.get_current().video_conference_server_url}-{self.group.id}-{self.group.secret_from_created}'
        context.update({
            'recording_prompt_required': recording_prompt_required,
            'has_bbb_video': self.has_bbb_video,
            'has_fairmeeting_video': self.has_fairmeeting_video,
            'meeting_url': meeting_url,
            'meeting_name': self.group.name,
            'group': self.group,
        })
        print(f'>< context {context}')
        return context


class GroupMembersMapListView(GroupDetailView):

    template_name = 'cosinnus/group/group_members_map.html'


class GroupListView(EndlessPaginationMixin, ListAjaxableResponseMixin, GroupMembershipMixin, ListView):
    """ Deprecated, has been replaced by `cosinnus.views.map.TileView`! """
    model = CosinnusGroup
    template_name = 'cosinnus/group/group_list.html'
    items_template = 'cosinnus/group/group_list_items.html'
    serializer_class = GroupSimpleSerializer
    paginator_class = Paginator
    
    def get_queryset(self):
        group_plural_url_key = self.request.path.split('/')[1]
        group_class = group_model_registry.get_by_plural_key(group_plural_url_key, None)
        self.group_type = group_class.GROUP_MODEL_TYPE
        
        model = group_class or self.model
        if settings.COSINNUS_SHOW_PRIVATE_GROUPS_FOR_ANONYMOUS_USERS or self.request.user.is_authenticated:
            regular_groups = model.objects.get_cached()
            return regular_groups
        else:
            return list(model.objects.public())

    def get_context_data(self, **kwargs):
        ctx = super(GroupListView, self).get_context_data(**kwargs)
        members, pendings, admins, invited = [], [], [], []
        
        # for each group, put the user pk in the appropriate status list if the user is in the group
        # for this view, we do not care about other users, thus the reduced query
        for group in ctx['object_list']:
            _members, _pendings, _admins, _invited = [], [], [], []
            if self.request.user.is_authenticated:
                user_pk = self.request.user.pk
                try:
                    if user_pk in self.membership_class.objects.get_admins(group=group):
                        _admins.append(user_pk)
                    if user_pk in self.membership_class.objects.get_members(group=group):
                        _members.append(user_pk)
                    if user_pk in self.membership_class.objects.get_pendings(group=group):
                        _pendings.append(user_pk)
                    if user_pk in self.membership_class.objects.get_invited_pendings(group=group):
                        _invited.append(user_pk)
                except self.membership_class.DoesNotExist:
                    pass
            members.append(_members)
            pendings.append(_pendings)
            admins.append(_admins)
            invited.append(_invited)
            
        ctx.update({
            'rows': list(zip(ctx['object_list'], members, pendings, admins, invited)),
            'unpaginated_rows': self.object_list,
            'map_groups': self.object_list, # unpaginated groups
            'group_type': self.group_type,
        })
        return ctx


class GroupListMineView(RequireLoggedInMixin, GroupListView):
    """ Deprecated, has been replaced by `cosinnus.views.map.TileView`! """
    paginate_by = None
    
    def get_queryset(self):
        group_plural_url_key = self.request.path.split('/')[1]
        group_class = group_model_registry.get_by_plural_key(group_plural_url_key, None)
        self.group_type = group_class.GROUP_MODEL_TYPE
        model = group_class or self.model
        
        my_groups = model.objects.get_for_user(self.request.user)
        my_inactive_groups = model.objects.filter(portal_id=CosinnusPortal.get_current().id, is_active=False)
        if not check_user_superuser(self.request.user):
            # special case for the group-list: we can see inactive groups here that we are an admin of
            # filter for groups user is admin of if he isnt a superuser
            my_inactive_groups = my_inactive_groups.filter(id__in=model.objects.get_for_user_group_admin_pks(self.request.user, includeInactive=True))
            
        my_groups += list(my_inactive_groups)
        return my_groups


class GroupListMineDeactivatedView(RequireLoggedInMixin, GroupListView):
    paginate_by = None
    
    def get_queryset(self):
        self.group_type = None
        return self.model.objects.get_deactivated_for_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        ctx = super(GroupListMineDeactivatedView, self).get_context_data(**kwargs)
        ctx.update({
            'hide_group_map': True,
            'is_deactivated_groups_view': True,
        })
        return ctx


class GroupListInvitedView(RequireLoggedInMixin, GroupListView):
    paginate_by = None
    
    def get_queryset(self):
        if self.kwargs.get('show_all', False):
            model = CosinnusGroup
            self.group_type = 'all'
        else:
            group_plural_url_key = self.request.path.split('/')[1]
            group_class = group_model_registry.get_by_plural_key(group_plural_url_key, None)
            self.group_type = group_class.GROUP_MODEL_TYPE
            model = group_class or self.model
        
        my_invited_groups = list(model.objects.get_for_user_invited(self.request.user))
        # add groups that a user was only recruited for, but not invited by an admin
        recruited_ids = self.request.user.cosinnus_profile.settings.get('group_recruits', [])
        if recruited_ids:
            my_invited_groups = my_invited_groups + list(model.objects.get_cached(pks=recruited_ids))
        
        return my_invited_groups
    
    def get_context_data(self, **kwargs):
        ctx = super(GroupListInvitedView, self).get_context_data(**kwargs)
        ctx.update({'hide_group_map': True})
        return ctx


class FilteredGroupListView(GroupListView):
    """ This will show 'related' groups and projects.
        For a given group slug, will only show the group itself.
        For a given project slug, will show all projects in the same group as that project,
            or just itself if it isn't in a group. """
    
    def get(self, request, *args, **kwargs):
        self.group_slug = kwargs.pop('group')
        try:
            self.filter_group = CosinnusGroup.objects.get_cached(slugs=self.group_slug)
        except CosinnusGroup.DoesNotExist:
            raise Http404
        return super(FilteredGroupListView, self).get(request, *args, **kwargs)
    
    def get_queryset(self):
        qs_list = super(FilteredGroupListView, self).get_queryset()
        if not self.filter_group.parent_id:
            return [self.filter_group]
        return [group for group in qs_list if group.parent_id==self.filter_group.parent_id]
    
    def get_context_data(self, **kwargs):
        ctx = super(FilteredGroupListView, self).get_context_data(**kwargs)
        ctx.update({'filter_group': self.filter_group})
        return ctx


class GroupMapListView(GroupListView):
    template_name = 'cosinnus/group/group_list_map.html'


class GroupUpdateView(SamePortalGroupMixin, CosinnusGroupFormMixin, 
                      AttachableViewMixin, AvatarFormMixin, AjaxableFormMixin, UserFormKwargsMixin,
                      RequireAdminMixin, UpdateWithInlinesView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!
    
    form_view = 'edit'
    
    message_success = _('The %(team_type)s was changed successfully.')
    
    def get_object(self, queryset=None):
        return self.group
    
    def get_initial(self):
        """ Allow pre-populating managed tags on group edit from initial default tags """
        initial = super().get_initial()
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_GROUPS:
            if settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG is not None:
                initial['managed_tag_field'] = settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG
        return initial

    def get_context_data(self, **kwargs):
        context = super(GroupUpdateView, self).get_context_data(**kwargs)

        invite_tokens = []
        if 'invite_token' in self.group.settings:
            token = self.group.settings.get('invite_token', None)
            invite_tokens = token and CosinnusGroupInviteToken.objects.filter(portal=self.group.portal, token__iexact=token) or []

        context.update({
            'submit_label': _('Save'),
            'group': self.group,
            'invite_tokens': invite_tokens,
            }
        )
        return context
    
    def get_form_kwargs(self):
        kwargs = super(GroupUpdateView, self).get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs

    def check_fields_changed(self, field_names, form):
        if self.group.id:
            form_data = form.cleaned_data.get('obj')
            obj = CosinnusConference.objects.get(id=self.group.id)
            for field_name in field_names:
                form_field_value = form_data.get(field_name)
                if isinstance(form_field_value, datetime.datetime):
                    form_field_value = form_field_value.astimezone(pytz.utc)
                instance_field_value = getattr(obj, field_name)
                if not form_field_value == instance_field_value:
                    return True
        return False

    def forms_valid(self, form, inlines):
        if self.group.__class__.__name__ == 'CosinnusConference':
            obj = self.group
            times_changed = self.check_fields_changed(
                ['from_date', 'to_date'], form)
            details_changed = self.check_fields_changed(
                ['name', 'description'], form)
            if details_changed or (times_changed and details_changed):
                cosinnus_notifications.attending_conference_changed.send(
                    sender=self.group, user=self.request.user, obj=obj,
                    audience=get_user_model().objects.filter(
                        id__in=self.group.members)
                )
            elif times_changed:
                cosinnus_notifications.attending_conference_time_changed.send(
                    sender=self.group, user=self.request.user, obj=obj,
                    audience=get_user_model().objects.filter(
                        id__in=self.group.members)
                )
        messages.success(self.request, self.message_success % {'team_type':self.object._meta.verbose_name})
        return super(GroupUpdateView, self).forms_valid(form, inlines)


class GroupUserListView(ListAjaxableResponseMixin, RequireReadMixin, ListView):

    serializer_class = UserSerializer
    template_name = 'cosinnus/group/group_user_list.html'

    def get_queryset(self):
        return self.group.users.all()


class GroupConfirmMixin(object):
    model = CosinnusGroup
    slug_url_kwarg = 'group'
    success_url = reverse_lazy('cosinnus:group-list')
    
    def get(self, *args, **kwargs):
        """ We make the allowance to call this by GET if called with ?direct=1 param,
            so that user joins can be automated with a direct link (like after being recruited) """
        if not self.request.GET.get('direct', None) == '1':
            messages.error(self.request, _('This action is not available directly!'))
            return redirect(self.get_error_url(**kwargs))
        else:
            return self.post(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.confirm_action()
        # update index for the group
        self.object.update_index()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_str(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def get_error_url(self, **kwargs):
        return group_aware_reverse('cosinnus:group-detail', kwargs=kwargs)

    def confirm_action(self):
        raise NotImplementedError()


class GroupUserJoinView(SamePortalGroupMixin, GroupConfirmMixin, GroupMembershipMixin, DetailView):

    message_success = _('You have requested to join the %(team_type)s “%(team_name)s”. You will receive an email as soon as a team administrator responds to your request.')
    referer_url = reverse_lazy('cosinnus:group-list')
    membership_status = MEMBERSHIP_MEMBER

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserJoinView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        # do not allow this for conferences with application management, because
        # invitations are done via the application form
        self.object = self.get_object()
        if self.object.group_is_conference and self.object.use_conference_applications:
            raise PermissionDenied()
        self.referer = request.META.get('HTTP_REFERER', self.referer_url)
        return super(GroupUserJoinView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer
    
    def confirm_action(self):
        # default membership status is pending, so if we are already pending or a member, nothing happens,
        # and if we have no relation to the group, a new pending membership is created.
        try:
            m = self.membership_class.objects.get(
                user=self.request.user,
                group=self.object,
            )
            # if member was already invited when asking to join, make him a member immediately
            if m.status == MEMBERSHIP_INVITED_PENDING:
                m.status = self.membership_status
                m.save()
                messages.success(self.request, _('You had already been invited to "%(team_name)s" and have now been made a member immediately!') % {'team_name': self.object.name})
                signals.user_group_invitation_accepted.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
        except self.membership_class.DoesNotExist:
            # auto-join groups will accept immediately
            if self.object.is_autojoin_group:
                self.membership_class.objects.create(
                    user=self.request.user,
                    group=self.object,
                    status=self.membership_status
                )
                messages.success(self.request, _('You are now a member of %(team_type)s “%(team_name)s”. Welcome!') % {'team_name': self.object.name, 'team_type':self.object._meta.verbose_name})
            else:
                self.membership_class.objects.create(
                    user=self.request.user,
                    group=self.object,
                    status=MEMBERSHIP_PENDING
                )
                signals.user_group_join_requested.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
                messages.success(self.request, self.message_success % {'team_name': self.object.name, 'team_type':self.object._meta.verbose_name})
        self.referer = self.object.get_absolute_url()


class CSRFExemptGroupJoinView(GroupUserJoinView):
    """ A CSRF-exempt group user join view that only works on autojoin groups.
    """
    
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(CSRFExemptGroupJoinView, self).dispatch(*args, **kwargs)
    
    def get_object(self, *args, **kwargs): 
        group = super(CSRFExemptGroupJoinView, self).get_object(*args, **kwargs)
        if group and not group.is_autojoin_group:
            raise PermissionDenied('The group/project requested for the join is not marked as auto-join!')
        return group


class GroupUserLeaveView(SamePortalGroupMixin, GroupConfirmMixin, GroupMembershipMixin, DetailView):

    message_success = _('You are no longer a member of the %(team_type)s “%(team_name)s”.')
    
    @method_decorator(login_required)
    @atomic
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserLeaveView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.referer = request.META.get('HTTP_REFERER', reverse('cosinnus:group-list'))
        return super(GroupUserLeaveView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        if not getattr(self, '_had_error', False):
            messages.success(self.request, self.message_success % {'team_name': self.object.name, 'team_type':self.object._meta.verbose_name})
        return self.referer
    
    def confirm_action(self):
        self._had_error = False
        
        admins = self.membership_class.objects.get_admins(group=self.object)
        if len(admins) > 1 or self.request.user.pk not in admins:
            try:
                membership = self.membership_class.objects.get(
                    user=self.request.user,
                    group=self.object,
                    status=MEMBERSHIP_MEMBER if self.request.user.pk not in admins else MEMBERSHIP_ADMIN
                )
                membership.delete()
            except self.membership_class.DoesNotExist:
                self._had_error = True
        else:
            self._had_error = True
            messages.error(self.request,
                _('You cannot leave this %(team_type)s. You are the only administrator left.') % { 'team_type':self.object._meta.verbose_name}
            )


class GroupUserWithdrawView(SamePortalGroupMixin, GroupConfirmMixin, GroupMembershipMixin, DetailView):

    message_success = _('Your join request was withdrawn from %(team_type)s “%(team_name)s” successfully.')
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserWithdrawView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.referer = request.META.get('HTTP_REFERER', reverse('cosinnus:group-list'))
        return super(GroupUserWithdrawView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        if not getattr(self, '_had_error', False):
            messages.success(self.request, self.message_success % {'team_name': self.object.name, 'team_type':self.object._meta.verbose_name})
        return self.referer
    
    def confirm_action(self):
        try:
            membership = self.membership_class.objects.get(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_PENDING
            )
            membership.delete()
        except self.membership_class.DoesNotExist:
            self._had_error = True


class GroupUserInvitationDeclineView(GroupUserWithdrawView):

    message_success = _('You have declined the invitation to %(team_type)s “%(team_name)s”.')
    
    def confirm_action(self):
        try:
            membership = self.membership_class.objects.get(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_INVITED_PENDING
            )
            membership.delete()
            signals.user_group_invitation_declined.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
        except self.membership_class.DoesNotExist:
            self._had_error = True


class GroupUserInvitationAcceptView(GroupUserWithdrawView):

    message_success = _('You are now a member of %(team_type)s “%(team_name)s”. Welcome!')
    membership_status = MEMBERSHIP_MEMBER
    
    def post(self, request, *args, **kwargs):
        # do not allow this for conferences with application management, because
        # invitations are done via the application form
        self.object = self.get_object()
        if self.object.group_is_conference and self.object.use_conference_applications:
            raise PermissionDenied()
        return super(GroupUserInvitationAcceptView, self).post(request, *args, **kwargs)
    
    def confirm_action(self):
        try:
            membership = self.membership_class.objects.get(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_INVITED_PENDING
            )
            membership.status = self.membership_status
            membership.save()
            signals.user_group_invitation_accepted.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
        except self.membership_class.DoesNotExist:
            self._had_error = True


class UserSelectMixin(object):
    form_class = MembershipForm
    model = CosinnusGroupMembership
    slug_field = 'user__username'
    slug_url_kwarg = 'username'

    @atomic
    def dispatch(self, request, *args, **kwargs):
        return super(UserSelectMixin, self).dispatch(request, *args, **kwargs)
    
    def get(self, *args, **kwargs):
        messages.error(self.request, _('This action is not available directly!'))
        return redirect(group_aware_reverse('cosinnus:group-detail', kwargs={'group': kwargs.get('group', '<NOGROUPKWARG>')}))

    def get_form_kwargs(self):
        kwargs = super(UserSelectMixin, self).get_form_kwargs()
        kwargs['group'] = self.group
        kwargs['user_qs'] = self.get_user_qs()
        return kwargs

    def get_initial(self):
        username = self.kwargs.get('username', None)
        if username:
            user = get_user_model()._default_manager.get(username=username)
            return {'user': user}

    def get_queryset(self):
        return self.model.objects.filter(group=self.group)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group})


class GroupUserInviteView(AjaxableFormMixin, RequireAdminMixin, UserSelectMixin,
                       CreateView):
    
    #TODONEXT: delete this view probably!
    
    template_name = 'cosinnus/group/group_detail.html'
    invite_subject = _('I invited you to join "%(team_name)s"!')
    invite_template_name = 'cosinnus/mail/user_group_invited_direct_message.txt'
    membership_status = MEMBERSHIP_MEMBER

    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        try:
            m = self.model.objects.get(user=user, group=self.group)
            # if the user has already requested a join when we try to invite him, accept him immediately
            if m.status == MEMBERSHIP_PENDING:
                m.status = self.membership_status
                m.save()
                # update index for the group
                self.group.update_index()
                signals.user_group_join_accepted.send(sender=self, obj=self.group, user=user, audience=[user])
                messages.success(self.request, _('User %(username)s had already requested membership and has now been made a member immediately!') % {'username': user.get_full_name()})
                # trigger signal for accepting that user's join request
            return HttpResponseRedirect(self.get_success_url())
        except self.model.DoesNotExist:
            ret = super(GroupUserInviteView, self).form_valid(form)
            signals.user_group_invited.send(sender=self, obj=self.object.group, user=self.request.user, audience=[user])
            # we will also send out an internal direct message about the invitation to the user
            try:
                from cosinnus_message.utils.utils import write_postman_message
                subject = self.invite_subject % {'team_name': self.object.group.name}
                data = {
                    'user': user,
                    'group': self.object.group,
                }
                text = render_to_string(self.invite_template_name, data)
                write_postman_message(user, self.request.user, subject, text)
            except ImportError:
                pass
        
            messages.success(self.request, _('User %(username)s was successfully invited!') % {'username': user.get_full_name()})
            return ret

    def get_user_qs(self):
        uids = self.model.objects.get_members(group=self.group)
        return get_user_model()._default_manager.exclude(id__in=uids)


class GroupInviteMultipleView(RequireAdminMixin, GroupMembershipMixin, FormView):
    form_class = MultiGroupSelectForm

    def get(self, *args, **kwargs):
        messages.error(self.request, _('This action is not available directly!'))
        return redirect(group_aware_reverse('cosinnus:group-detail', kwargs={'group': kwargs.get('group', '<NOGROUPKWARG>')}))

    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs

    def form_valid(self, form):
        groups = form.cleaned_data.get('groups')
        invited_users = []
        if 'invited_users' in self.group.settings:
            invited_users = self.group.settings.get('invited_users')
        else:
            self.group.settings['invited_users'] = invited_users

        group_ids = [group.id for group in groups]

        if 'invited_groups' in self.group.settings:
            invited_groups = self.group.settings.get('invited_groups')
            for group_id in group_ids:
                if not group_id in invited_groups:
                    invited_groups.append(group_id)
        else:
            self.group.settings['invited_groups'] = group_ids
            
        # get all users of the selected groups
        memberships = CosinnusGroupMembership.objects.get_members(groups=group_ids)
        member_id_list = list(set([user for sub_list in memberships.values() for user in sub_list]))
        
        # get users who already got invitations or have applied
        already_applied_id_list = list(self.group.conference_applications.all().values_list('user__id', flat=True))
        currently_notified_id_list = list(set(self.group.members + self.group.invited_pendings + already_applied_id_list))
        
        member_list = filter_active_users(get_user_model().objects.filter(id__in=member_id_list).exclude(id__in=currently_notified_id_list))
        newly_invited_users = []
        for user in member_list:
            if not user.id in invited_users and not user.id == self.request.user.id:
                # send conference invitations to all users who haven't been invited, and never to self
                self.group.add_member_to_group(user, MEMBERSHIP_INVITED_PENDING)
                cosinnus_notifications.user_conference_invited_to_apply.send(
                    sender=self,
                    obj=self.group,
                    user=self.request.user,
                    audience=[user]
                )
                invited_users.append(user.id)
                newly_invited_users.append(user)
        
        # save the invited users and groups
        self.group.save()
        if newly_invited_users:
            messages.success(self.request, _('The following users were invited to apply: %s') % ', '.join(full_name(user) for user in newly_invited_users))
        else:
            messages.info(self.request, _('All members of groups/projects you selected had already been invited or have already applied. No new invitations have been sent.'))
        return HttpResponseRedirect(self.get_success_url())


class GroupUserInviteMultipleView(RequireAdminMixin, GroupMembershipMixin, FormView):
    
    form_class = MultiUserSelectForm
    template_name = 'cosinnus/group/group_detail.html'
    invite_subject = _('I invited you to join "%(team_name)s"!')
    invite_template_name = 'cosinnus/mail/user_group_invited_direct_message.txt'
    membership_status = MEMBERSHIP_MEMBER

    def get(self, *args, **kwargs):
        messages.error(self.request, _('This action is not available directly!'))
        return redirect(group_aware_reverse('cosinnus:group-detail', kwargs={'group': kwargs.get('group', '<NOGROUPKWARG>')}))

    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group})
    
    def get_form_kwargs(self):
        kwargs = super(GroupUserInviteMultipleView, self).get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs
    
    def form_valid(self, form):
        users = form.cleaned_data.get('users')
        for user in users:
            self.do_invite_valid_user(user, form)
        return HttpResponseRedirect(self.get_success_url())
    
    #TODONEXT: error handling!
    
    def do_invite_valid_user(self, user, form):
        try:
            m = self.membership_class.objects.get(user=user, group=self.group)
            # if the user has already requested a join when we try to invite him, accept him immediately
            if m.status == MEMBERSHIP_PENDING:
                m.status = self.membership_status
                m.save()
                # update index for the group
                self.group.update_index()
                signals.user_group_join_accepted.send(sender=self, obj=self.group, user=user, audience=[user])
                messages.success(self.request, _('User %(username)s had already requested membership and has now been made a member immediately!') % {'username': user.get_full_name()})
                # trigger signal for accepting that user's join request
            return HttpResponseRedirect(self.get_success_url())
        except self.membership_class.DoesNotExist:
            self.membership_class.objects.create(user=user, group=self.group, status=MEMBERSHIP_INVITED_PENDING)
            signals.user_group_invited.send(sender=self, obj=self.group, user=self.request.user, audience=[user])

            # sends a direct message about the invitation to the user (non-rocketchat only)            
            #TODONEXT: refactor messages into one!
            # we will also send out an internal direct message about the invitation to the user
            if not settings.COSINNUS_ROCKET_ENABLED:
                try:
                    from cosinnus_message.utils.utils import write_postman_message
                    subject = self.invite_subject % {'team_name': self.group.name}
                    data = {
                        'user': user,
                        'group': self.group,
                    }
                    text = render_to_string(self.invite_template_name, data)
                    write_postman_message(user, self.request.user, subject, text)
                except ImportError:
                    pass
        
            messages.success(self.request, _('User %(username)s was successfully invited!') % {'username': user.get_full_name()})
            return HttpResponseRedirect(self.get_success_url())


class GroupUserUpdateView(AjaxableFormMixin, RequireAdminMixin,
                          UserSelectMixin, UpdateView):

    membership_status = MEMBERSHIP_MEMBER

    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        self.object = self.get_object()
        current_status = self.object.status
        new_status = form.cleaned_data.get('status')
        
        if user.is_guest:
            messages.error(self.request, _('You cannot promote a guest user account!'))
        elif current_status == MEMBERSHIP_ADMIN and new_status != MEMBERSHIP_ADMIN and len(self.group.admins) <= 1:
            messages.error(self.request, _('You cannot remove “%(username)s” form '
                'this team. Only one admin left.') % {'username': full_name(user)})
        else:
            if current_status == MEMBERSHIP_PENDING and new_status == self.membership_status:
                signals.user_group_join_accepted.send(sender=self, obj=self.group, user=user, audience=[user])
            if current_status in [MEMBERSHIP_PENDING, self.membership_status] and new_status == MEMBERSHIP_ADMIN \
                    and not user.id == self.request.user.id:
                cosinnus_notifications.user_group_made_admin.send(sender=self, obj=self.object.group, user=self.request.user, audience=[user])
            elif current_status == MEMBERSHIP_ADMIN and new_status in [MEMBERSHIP_PENDING, self.membership_status] \
                    and not user.id == self.request.user.id:
                cosinnus_notifications.user_group_admin_demoted.send(sender=self, obj=self.object.group, user=self.request.user, audience=[user])
            ret = super(GroupUserUpdateView, self).form_valid(form)
            # update index for the group
            self.object._refresh_cache()
            self.object.group.update_index()
            return ret
        return HttpResponseRedirect(self.get_success_url())

    def get_user_qs(self):
        return self.group.users


class GroupUserDeleteView(AjaxableFormMixin, RequireAdminMixin, DeleteView):
    model = CosinnusGroupMembership
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
    membership_status = MEMBERSHIP_MEMBER

    @atomic
    def form_valid(self, form):
        self.object = self.get_object()
        group = self.object.group
        user = self.object.user
        current_status = self.object.status
        if (len(group.admins) > 1 or not group.is_admin(user)):
            if user != self.request.user or check_user_superuser(self.request.user):
                self.object.delete()

            else:
                messages.error(self.request, _('You cannot remove yourself from a %(team_type)s.') % {
                    'team_type': self.object._meta.verbose_name})
                return HttpResponseRedirect(self.get_success_url())
        else:
            messages.error(self.request, _('You cannot remove "%(username)s" form '
                                           'this team. Only one admin left.') % {'username': user.get_full_name()})
            return HttpResponseRedirect(self.get_success_url())

        if current_status == MEMBERSHIP_PENDING:
            signals.user_group_join_declined.send(sender=self, obj=group, user=user, audience=[user])
            messages.success(self.request,
                             _('Your join request was withdrawn from %(team_type)s "%(team_name)s" successfully.') % {
                                 'team_type': self.object._meta.verbose_name, 'team_name': group.name})
        if current_status == MEMBERSHIP_INVITED_PENDING:
            messages.success(self.request, _('Your invitation to user "%(username)s" was withdrawn successfully.') % {
                'username': user.get_full_name()})
        if current_status == self.membership_status:
            messages.success(self.request,
                             _('User "%(username)s" is no longer a member.') % {'username': user.get_full_name()})
        return HttpResponseRedirect(self.get_success_url())

    def get_queryset(self):
        return self.model.objects.filter(group=self.group)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group})


class GroupExportView(SamePortalGroupMixin, RequireAdminMixin, TemplateView):

    template_name = 'cosinnus/group/group_export.html'

    def get_context_data(self, **kwargs):
        export_apps = []
        for app, name, label in list(app_registry.items()):
            try:
                url = group_aware_reverse('cosinnus:%s:export' % name,
                              kwargs={'group': self.group})
            except NoReverseMatch:
                continue
            export_apps.append({'label': label, 'export_url': url})

        context = super(GroupExportView, self).get_context_data(**kwargs)
        context.update({
            'export_apps': export_apps,
        })
        return context


class ActivateOrDeactivateGroupView(TemplateView):
    
    template_name = 'cosinnus/group/group_activate_or_deactivate.html'
    
    message_success_activate = _('%(team_name)s was re-activated successfully!')
    message_success_deactivate = _('%(team_name)s was deactivated successfully!\n\nShould you wish to delete it permanently, please send an email to the administrators of the portal. Please send the email from the email account with which you are registered at this platform and add the exact name to the email, so that the administrators can verify your request.')
    
    def dispatch(self, request, *args, **kwargs):
        group_id = int(kwargs.pop('group_id'))
        self.activate = kwargs.pop('activate')
        group = get_object_or_404(CosinnusGroup, id=group_id)
        is_admin = check_user_superuser(request.user) or check_ug_admin(request.user, group)
        
        # only admins and group admins may deactivate groups/projects
        if not is_admin:
            messages.warning(self.request, group.trans.MESSAGE_ONLY_ADMINS_MAY_DEACTIVATE)
            return redirect_to_403(request, self)
        
        if group.is_active and self.activate or (not group.is_active and not self.activate):
            if self.activate:
                messages.warning(self.request, _('This project/group is already active!'))
            else:
                messages.warning(self.request, _('This project/group is already inactive!'))
            return redirect(reverse('cosinnus:profile-detail'))
            
        self.group = group
        return super(ActivateOrDeactivateGroupView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.group.is_active = self.activate
        # we need to manually reindex or remove index to be sure the index gets removed
        if not self.activate:
            # need to get a typed group first and remove it from index, because after saving it deactived the manager won't find it
            typed_group = ensure_group_type(self.group)
            typed_group.remove_index()
            typed_group.remove_index_for_all_group_objects()
            
        self.group.save() 
        # no clearing cache necessary as save() handles it
        if self.activate:
            typed_group = ensure_group_type(self.group)
            typed_group.update_index()
            typed_group.update_index_for_all_group_objects()
            messages.success(request, self.message_success_activate % {'team_name': self.group.name})
            return redirect(self.group.get_absolute_url())
        else:
            messages.success(request, self.message_success_deactivate % {'team_name': self.group.name})
            return redirect(reverse('cosinnus:profile-detail'))
    
    def get_context_data(self, **kwargs):
        context = super(ActivateOrDeactivateGroupView, self).get_context_data(**kwargs)
        context.update({
            'target_group': ensure_group_type(self.group),
            'activate': self.activate,
        })
        return context


class GroupStartpage(View):
    """ This view is in place as first starting point for the initial group frontpage.
        It decides whether the actual group dashboard or the group microsite should be shown. """
    
    dashboard_view = staticmethod(GroupDashboard.as_view())
    microsite_view = staticmethod(GroupMicrositeView.as_view())
    
    def check_redirect_to_microsite(self, request):
        """ Checks whether the user should be shown the Group Dashboard, the Group Micropage,
            or be redirected to a completely different page 
            @return: ``True`` if the group micropage should be shown
            @return: ``False`` if the group dashboard should be shown
            @return: ``<string>`` the URL that should be redirected to
        """
        # settings switch
        if not getattr(settings, 'COSINNUS_MICROSITES_ENABLED', False):
            return False
        
        if not request.user.is_authenticated:
            # if microsite access is limited, only allow invite-links, but nothing else
            if getattr(settings, 'COSINNUS_MICROSITES_DISABLE_ANONYMOUS_ACCESS', False) \
                    and not request.GET.get('invited', None) == '1':
                return False
            else:
                # if the group is not accessible, redirect to microsite 
                #   in case if the group's microsite should not be closed for the non-authenticated users
                if not check_object_read_access(self.group, request.user) and not self.group.is_publicly_visible:
                    return False
                return True

        # check if this session user has clicked on "browse" for this group before
        # and if so, never let him see that groups microsite again
        group_session_browse_key = 'group__browse__%s' % self.group.slug
        if self.request.GET.get('browse', False):
            request.session[group_session_browse_key] = True
            request.session.save()
            return request.path # redirect to URL without GET param
        if request.session.get(group_session_browse_key, False):
            return False
        
        if self.request.GET.get('microsite', None):
            return True
        
        if not request.user.pk in self.group.members:
            # non-members never see the dashboard, but always the microsite
            if self.group.group_is_conference:
                return True
            
            # grant access to superusers but notifiy them
            if check_user_superuser(request.user):
                messages.info(request, _('You are not a member, but have access because you are an Administrator.'))
                return False
            return True
        return False
    
    @dispatch_group_access()
    def dispatch(self, request, *args, **kwargs):
        # lock conference groups to microsite if setting enabled
        if self.group.group_is_conference and settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
            return self.microsite_view(request, *args, **kwargs)
        
        redirect_result = self.check_redirect_to_microsite(request)
        if isinstance(redirect_result, six.string_types):
            return redirect(redirect_result)
        elif redirect_result:
            return self.microsite_view(request, *args, **kwargs)
        else:
            return self.dashboard_view(request, *args, **kwargs)


@csrf_protect
def group_user_recruit(request, group,
                       membership_class=CosinnusGroupMembership,
                       invite_class=CosinnusUnregisterdUserGroupInvite,
                       membership_status=MEMBERSHIP_MEMBER):
    """ Invites users to become group members by creating a CosinnusUnregisterdUserGroupInvite for each email to be recruited.
        Checks for recent invites and existing ones first. 
        Sends out invitation mails to newly invited users. """
    
    MAXIMUM_EMAILS = 50
    
    if not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    
    # resolve group either from the slug, or like the permission group mixin does it
    # (group type needs to also be used for that)
    group = get_group_for_request(group, request)
    if not group:
        logger.error('No group found when trying to recruit users!', extra={'group_slug': group, 
            'request': request, 'path': request.path})
        return redirect(reverse('cosinnus:group-list'))
    
    emails = request.POST.get('emails', '')
    msg = request.POST.get('message', '').strip()
    user = request.user
    redirect_url = request.META.get('HTTP_REFERER', group_aware_reverse('cosinnus:group-detail', kwargs={'group': group}))
    
    # do permission checking using has_write_access(request.user, group)
    # TODO: make this available to group.members soon!
    if not is_superuser(user) and not user.id in group.admins:
        logger.error('Permission error when trying to recruit users!', 
             extra={'user': request.user, 'request': request, 'path': request.path, 'group_slug': group})
        messages.error(request, _('Only group/project members have permission to do this!'))
        return redirect(redirect_url)
    
    # flag for admins who may issue direct invites instead of just recruits
    is_group_admin = user.id in group.admins
    invalid = []
    existing_already_members = []
    existing_already_invited = []
    existing_newly_invited = []
    
    spam_protected = []
    success = []
    prev_invites_to_refresh = []
    
    # format and validate emails
    emails = emails.lower().replace(';', ',').replace('\n', ',').replace('\r', ',').split(',')
    emails = list(set([email.strip(' \t\n\r') for email in emails]))
    
    for email in emails:
        # stop after 20 fragments to prevent malicious overloading
        if len(invalid) + len(existing_already_members) + len(existing_already_invited) \
                + len(existing_newly_invited) + len(success) > MAXIMUM_EMAILS:
            messages.warning(request, _('You may only invite %(maximum_number)d people at once. Any emails above that number have been ignored.') % {'maximum_number': MAXIMUM_EMAILS})
            break
        
        if not email:
            continue
        try:
            validate_email(email)
        except ValidationError:
            invalid.append(email)
            continue
        
        # from here on, we have a real email. check if a user with that email exists
        existing_user = get_object_or_None(get_user_model(), email__iexact=email)
        if existing_user:
            # check if there is already a group membership for this user
            membership = get_object_or_None(membership_class, group=group, user=existing_user)
            if not membership:
                # user exists, invite him via email, or directy on the platform if the user is an admin
                if is_group_admin:
                    membership_class.objects.create(group=group, user=existing_user, status=MEMBERSHIP_INVITED_PENDING)
                    existing_newly_invited.append(email)
                else:
                    # currently unreachable because recruit only works as group admins
                    # TODO: once recruiting is enabled for group-members, we need a solution for what to do here!
                    invalid.append(email)
            elif membership.status in MEMBER_STATUS:
                # user is already a member
                existing_already_members.append(email)
            elif membership.status == MEMBERSHIP_PENDING:
                # user has already requested to join, make member if group admin
                if is_group_admin:
                    membership.status = membership_status
                    membership.save()
                    existing_newly_invited.append(email)
                else:
                    existing_already_invited.append(email)
            elif membership.status == MEMBERSHIP_INVITED_PENDING:
                # we have already invited the user on the platform
                existing_already_invited.append(email)
            else:
                logger.error('Group member recruit: An unreachable else case was reached. Were the membership statuses expanded?')
            # since we handled this invite, delete all previous recruit-invitations
            prev_invites = invite_class.objects.filter(email__iexact=email, group=group)
            if prev_invites.count() > 0:
                prev_invites.delete()
            continue
        
        
        # check if the user has been invited recently (if so, we don't send another mail)
        prev_invites = invite_class.objects.filter(email__iexact=email, group=group).order_by('-last_modified')
        prev_invite = prev_invites[0] if len(prev_invites) > 0 else None
        if prev_invite and prev_invite.last_modified > (now() - datetime.timedelta(days=1)):
            spam_protected.append(email)
            continue
        success.append(email)
        if prev_invite:
            prev_invites_to_refresh.append(prev_invite)
    
    # we attach the additional message to the object description (in this case our sender profile):
    if msg:
        content = mark_safe(render_to_string('cosinnus/html_mail/content_snippets/recruit_personal_message.html', {'sender': user}))
        msg = mark_safe(linebreaksbr(escape(msg)))
        def render_additional_notification_content_rows():
            return [content, msg]
        group_copy = deepcopy(group) # we deepcopy to avoid getting the attached function cached for this group
        setattr(group_copy, 'render_additional_notification_content_rows', render_additional_notification_content_rows)
    else:
        group_copy = group

    # collect target emails        
    virtual_target_users = []
    for email in success:
        virtual_user = AnonymousUser()
        virtual_user.email = email
        virtual_target_users.append(virtual_user)
    # send emails as single notification signal
    signals.user_group_recruited.send(sender=user, obj=group_copy, user=user, audience=virtual_target_users)
    
    # create invite objects
    with transaction.atomic():
        for email in success:
            just_refresh_invites = [inv for inv in prev_invites_to_refresh if inv.email.lower() == email]
            if just_refresh_invites:
                if is_group_admin:
                    just_refresh_invites[0].invited_by = user
                just_refresh_invites[0].save()
                continue
            # we always create an initial object here, even if the user is not admin.
            # the invite permission is checked on user join 
            invite_class.objects.create(email=email, group=group, invited_by=user)
    
    if invalid:
        messages.error(request, _("Sorry, these did not seem to be valid email addresses: %s") % ', '.join(invalid))
    if spam_protected:
        messages.warning(request, _("These people have been sent an email invite only recently. You can send them an invite again tomorrow: %s") % ', '.join(spam_protected))
    if existing_already_members:
        messages.success(request, _("Good news! The people with these addresses are already members: %s") % ', '.join(existing_already_members))
    if existing_already_invited:
        messages.warning(request, _("The people with these addresses already have a user account and already have a pending invitation: %s") % ', '.join(existing_already_invited))
    if existing_newly_invited:
        messages.success(request, _("The people with these addresses already have a registered user account and have been invited directly: %s") % ', '.join(existing_newly_invited))
    if success:
        messages.success(request, _("Success! We are now sending out invitations to these email addresses: %s") % ', '.join(success))
        
    return redirect(redirect_url)


@csrf_protect
def group_user_recruit_delete(request, group, id, invite_class=CosinnusUnregisterdUserGroupInvite):
    """ Deletes a specific CosinnusUnregisterdUserGroupInvite """
    
    if not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    
    msg_error = _('There was an error when trying to delete the invitation.')
    msg_success = _('The invitation was successfully deleted.')
    
    # resolve group either from the slug, or like the permission group mixin does it
    # (group type needs to also be used for that)
    group = get_group_for_request(group, request)
    if not group:
        messages.error(request, msg_error)
        logger.error('No group found when trying to delete a recruited users!', extra={'group_slug': group, 
            'request': request, 'path': request.path})
        return redirect(reverse('cosinnus:group-list'))
    
    group_redirect = redirect(group_aware_reverse('cosinnus:group-detail', kwargs={'group': group}))
    recruitation = get_object_or_None(invite_class, id=id)
    if not recruitation or not recruitation.group == group:
        messages.error(request, msg_error)
        return group_redirect
    # check permissions
    if not (request.user.id == recruitation.invited_by_id or check_object_write_access(group, request.user)):
        messages.error(request, msg_error)
        return group_redirect
    
    # don't use .delete() on the object to avoid unnecessary cache deletes (recruitations aren't cached)
    invite_class.objects.filter(id=recruitation.id).delete()
    messages.success(request, msg_success)
    return group_redirect


@csrf_protect
def group_assign_reflected_object(request, group): 
    if not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated:
        raise PermissionDenied('Must be authenticated!')
    group = get_group_for_request(group, request)
    if not group:
        return HttpResponseBadRequest('Target group not found!')
    
    # parse params
    reflecting_object_id = request.POST.get('reflecting_object_id', None)
    reflecting_object_content_type = request.POST.get('reflecting_object_content_type', None)
    checked_groups = request.POST.getlist('group_checked', None)
    if reflecting_object_id is None or reflecting_object_content_type is None or checked_groups is None:
        return HttpResponseBadRequest('Missing POST parameters!')
    checked_groups = [int(group_id) for group_id in checked_groups]
    
    # get content type, check if among the allowed ones
    if not reflecting_object_content_type in getattr(settings, 'COSINNUS_REFLECTABLE_OBJECTS', []):
        raise PermissionDenied('This object type cannot be reflected!')
    app_label, model_str = reflecting_object_content_type.split('.',1)
    ct = ContentType.objects.get_by_natural_key(app_label, model_str)
    
    # get object
    model = ct.model_class()
    obj = get_object_or_None(model, id=reflecting_object_id)
    if not obj:
        return HttpResponseBadRequest('Target object not found!')
    # check if object really part of current group
    if not obj.group_id == group.id:
        return HttpResponseBadRequest('Object does not belong in this group!')
    # check user object read permission
    if not check_object_read_access(obj, request.user):
        raise PermissionDenied('You have no access to this object!')
    
    # get all reflectable groups and reflecting groups from mixin
    mixin = ReflectedObjectSelectMixin()
    reflect_data = mixin.get_reflect_data(request, group, obj)
    added_groups = []
    
    with transaction.atomic():
        for reflectable_group, reflecting in reflect_data['reflectable_groups']:
            # if in checked but not reflecting, create
            if reflectable_group.id in checked_groups and not reflecting:
                BaseTaggableObjectReflection.objects.create(content_type=ct, object_id=obj.id, group=reflectable_group, creator=request.user)
                added_groups.append(reflectable_group)
            # if in reflecting, but not active, get reflecting object, delete it
            if reflecting and not reflectable_group.id in checked_groups:
                BaseTaggableObjectReflection.objects.get(content_type=ct, object_id=obj.id, group=reflectable_group).delete()
            # just to display, unchanged reflecting groups
            if reflecting and reflectable_group.id in checked_groups:
                added_groups.append(reflectable_group)
    
    success_message = _('Your selection for showing this item in projects/groups was updated.')
    if added_groups:
        group_names = ', '.join([show_group.name for show_group in added_groups])
        success_message = force_str(success_message) + ' ' + force_str(_('This item is now being shown in these projects/groups: %(group_names)s') % {'group_names': group_names})
    messages.success(request, success_message)
    
    redirect_url = obj.get_absolute_url()
    return redirect(redirect_url)


class GroupInviteSelect2View(RequireReadMixin, Select2View):
    """
    This view is used as API backend to serve the suggestions for the group invite field.
    """

    def check_all_permissions(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied

    def get_results(self, request, term, page, context):
        terms = term.strip().lower().split(' ')
        q = get_group_query_filter_for_search_terms(terms)
        groups = get_cosinnus_group_model().objects.filter(q)
        groups = groups.filter(portal_id=CosinnusPortal.get_current().id, is_active=True)
        # non-superusers can only invite groups they are a member of
        if not check_user_superuser(request.user):
            user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(request.user)
            groups = groups.filter(id__in=user_group_ids)
        # do/do not return the forum group
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        if forum_slug:
            groups = groups.exclude(slug=forum_slug)
            
        if 'group' in self.kwargs and self.kwargs.get('group'):
            group = CosinnusGroup.objects.get(slug=self.kwargs.get('group'))
            exclude_ids = [group.id]
            if 'invited_groups' in group.settings:
                exclude_ids = exclude_ids + group.settings.get('invited_groups')
            groups = groups.exclude(id__in=exclude_ids)
        

        results = get_group_select2_pills(groups)

        # Any error response, Has more results, options list
        return (NO_ERR_RESP, False, results)


class UserGroupMemberInviteSelect2View(RequireReadMixin, Select2View):
    """
    This view is used as API backend to serve the suggestions for the group member invite field.
    """

    def check_all_permissions(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied

    def get_user_queryset(self, terms):
        # filter for active portal members that are not group members
        users = filter_active_users(get_user_model().objects.all())\
                .exclude(id__in=self.group.members)\
                .exclude(id__in=self.group.invited_pendings)
        # filter for query terms
        q = get_user_query_filter_for_search_terms(terms)
        users = users.filter(q)
        return users

    def get_results(self, request, term, page, context):
        terms = term.strip().lower().split(' ')
        
        users = self.get_user_queryset(terms)

        users = prioritize_suggestions_output(request, users)
        
        # as a last filter, remove all users that that have their privacy setting to "only members of groups i am in",
        # if they aren't in a group with the user
        users = [user for user in users if check_user_can_see_user(request.user, user)]
        
        # check for a direct email match
        direct_email_user = get_user_by_email_safe(term)
        if direct_email_user:
            # filter for members/pending/self manually
            if not direct_email_user.id in self.group.members \
                    and not direct_email_user.id in self.group.invited_pendings \
                    and not direct_email_user.id == request.user.id:
                users = [direct_email_user] + users
        
        results = get_user_select2_pills(users)

        # Any error response, Has more results, options list
        return (NO_ERR_RESP, False, results)


class GroupActivateAppView(SamePortalGroupMixin, AjaxableFormMixin, RequireAdminMixin, View):
    """ Deactivates the cosinnus app for a group passed via the "app" form field  """
    
    http_method_names = ['post',]
    model = CosinnusGroup
    slug_url_kwarg = 'group'
    message_success = _('The %s-app was activated!')

    @atomic
    def dispatch(self, *args, **kwargs):
        return super(GroupActivateAppView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        app = self.request.POST.get('app', None)
        # remove the given app from the deactivated list
        if app and app in app_registry.get_deactivatable_apps() and app in self.group.get_deactivated_apps():
            self.group.deactivated_apps = ','.join(list(set([
                prior_app for prior_app in self.group.get_deactivated_apps()
                if not prior_app == app
            ])))
            self.group.save(update_fields=['deactivated_apps'])
            signals.group_apps_activated.send(sender=self, group=self.group, apps=[app])
            messages.success(self.request, self.message_success % app_registry.get_label(app))
        return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': self.group}))


class GroupOrganizationsView(DetailView):
    template_name = 'cosinnus/group/organizations.html'
    model = get_cosinnus_group_model()
    slug_url_kwarg = 'group'

    def get_context_data(self, **kwargs):
        context = super(GroupOrganizationsView, self).get_context_data(**kwargs)
        queryset = self.object.organizations
        context.update({
            'requested': queryset.filter(status=MEMBERSHIP_PENDING),
            'invited': queryset.filter(status=MEMBERSHIP_INVITED_PENDING),
            'members': queryset.filter(status__in=MEMBER_STATUS),
            'request_form': MultiOrganizationSelectForm(group=self.object),
            'group': self.object,
        })
        return context


class GroupOrganizationRequestView(RequireAdminMixin, GroupMembershipMixin, FormView):
    form_class = MultiOrganizationSelectForm
    template_name = 'cosinnus/group/group_detail.html'
    message_success = _(
        'You have requested to join the organization “%(name)s”. You will receive an email as soon as a administrator responds to your request.')

    def get(self, *args, **kwargs):
        messages.error(self.request, _('This action is not available directly!'))
        return redirect(
            group_aware_reverse('cosinnus:group-organizations', kwargs={'group': kwargs.get('group', '<NOGROUPKWARG>')}))

    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-organizations', kwargs={'group': self.group})

    def get_form_kwargs(self):
        kwargs = super(GroupOrganizationRequestView, self).get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs

    def form_valid(self, form):
        organizations = form.cleaned_data.get('organizations')
        for organization in organizations:
            self.invite(organization, form)
        return HttpResponseRedirect(self.get_success_url())

    def invite(self, organization, form):
        try:
            m = CosinnusOrganizationGroup.objects.get(organization=organization, group=self.group)
            # if the group has already been invited when we try to request, assign it immediately
            if m.status == MEMBERSHIP_INVITED_PENDING:
                m.status = MEMBERSHIP_MEMBER
                m.save()
                # update index for the group
                # typed_group = ensure_group_type(self.group)
                # typed_group.update_index()
                signals.organization_group_invitation_accepted.send(sender=self, organization=organization, group=self.group)
                messages.success(self.request, _(
                    'Project/group %(group)s had already been invited and has now been assigned immediately!') % {
                                     'name': self.group.name})
                # trigger signal for accepting that user's join request
        except CosinnusOrganizationGroup.DoesNotExist:
            CosinnusOrganizationGroup.objects.create(organization=organization, group=self.group, status=MEMBERSHIP_PENDING)
            signals.organization_group_requested.send(sender=self, organization=organization, group=self.group)

            messages.success(self.request, self.message_success % {'name': organization.name})


class GroupOrganizationRequestSelect2View(RequireReadMixin, Select2View):
    """
    This view is used as API backend to serve the suggestions for the organization field.
    """

    def check_all_permissions(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

    def get_results(self, request, term, page, context):
        terms = term.strip().lower().split(' ')
        q = get_group_query_filter_for_search_terms(terms)

        organizations = CosinnusOrganization.objects.filter(q)
        organizations = organizations.filter(portal_id=CosinnusPortal.get_current().id, is_active=True)
        organizations = organizations.exclude(groups__group=self.group)
        organizations = [org for org in organizations if check_object_read_access(org, request.user)]
        organizations = sorted(organizations, key=lambda org: org.name.lower())

        results = get_organization_select2_pills(organizations)

        # Any error response, Has more results, options list
        return (NO_ERR_RESP, False, results)


class RemoveGroupInviteFromGroup(RequireReadMixin, FormView):

    def post(self, request, *args, **kwargs):
        if 'remove-group-invitation' in request.POST:
            group_id = int(request.POST.get('remove-group-invitation'))
            if 'invited_groups' in self.group.settings:
                invited_groups = self.group.settings.get('invited_groups')
                if group_id in invited_groups:
                    invited_groups.remove(group_id)
                    self.group.save()
        return HttpResponseRedirect(group_aware_reverse(
            'cosinnus:group-detail', kwargs={'group': self.group}))


group_group_invite_delete = RemoveGroupInviteFromGroup.as_view()
group_create = GroupCreateView.as_view()
group_create_api = GroupCreateView.as_view(is_ajax_request_url=True)
group_delete = GroupDeleteView.as_view()
group_delete_api = GroupDeleteView.as_view(is_ajax_request_url=True)
group_detail = GroupDetailView.as_view()
group_detail_api = GroupDetailView.as_view(is_ajax_request_url=True)
group_meeting = GroupMeetingView.as_view()
group_members_map = GroupMembersMapListView.as_view()
group_list = GroupListView.as_view()
group_list_api = GroupListView.as_view(is_ajax_request_url=True)
group_list_mine = GroupListMineView.as_view()
group_list_mine_deactivated = GroupListMineDeactivatedView.as_view()
group_list_invited = GroupListInvitedView.as_view()
group_list_filtered = FilteredGroupListView.as_view()
group_list_map = GroupMapListView.as_view()
group_update = GroupUpdateView.as_view()
group_update_api = GroupUpdateView.as_view(is_ajax_request_url=True)
group_user_list = GroupUserListView.as_view()
group_user_list_api = GroupUserListView.as_view(is_ajax_request_url=True)
group_user_join = GroupUserJoinView.as_view()
group_user_join_csrf_exempt = CSRFExemptGroupJoinView.as_view()
group_user_leave = GroupUserLeaveView.as_view()
group_user_withdraw = GroupUserWithdrawView.as_view()
group_user_invitation_decline = GroupUserInvitationDeclineView.as_view()
group_user_invitation_accept = GroupUserInvitationAcceptView.as_view()
group_user_add = GroupUserInviteView.as_view()
group_user_add_api = GroupUserInviteView.as_view(is_ajax_request_url=True)
group_user_add_multiple = GroupUserInviteMultipleView.as_view()
group_add_multiple = GroupInviteMultipleView.as_view()
group_user_update = GroupUserUpdateView.as_view()
group_user_update_api = GroupUserUpdateView.as_view(is_ajax_request_url=True)
group_user_delete = GroupUserDeleteView.as_view()
group_user_delete_api = GroupUserDeleteView.as_view(is_ajax_request_url=True)
group_export = GroupExportView.as_view()
activate_or_deactivate = ActivateOrDeactivateGroupView.as_view()
group_startpage = GroupStartpage.as_view()
user_group_member_invite_select2 = UserGroupMemberInviteSelect2View.as_view()
group_invite_select2 = GroupInviteSelect2View.as_view()
group_activate_app = GroupActivateAppView.as_view()
group_organizations = GroupOrganizationsView.as_view()
group_organization_request = GroupOrganizationRequestView.as_view()
group_organization_request_select2 = GroupOrganizationRequestSelect2View.as_view()
