# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import chain

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse, reverse_lazy, NoReverseMatch
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic import (CreateView, DeleteView, DetailView,
    ListView, UpdateView, TemplateView)

from cosinnus.core.decorators.views import membership_required, redirect_to_403,\
    dispatch_group_access, get_group_for_request
from cosinnus.core.registries import app_registry
from cosinnus.forms.group import MembershipForm, CosinnusLocationForm,\
    CosinnusGroupGalleryImageForm
from cosinnus.models.group import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING, CosinnusPortal, CosinnusLocation,
    CosinnusGroupGalleryImage, MEMBERSHIP_INVITED_PENDING)
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.models.serializers.group import GroupSimpleSerializer
from cosinnus.models.serializers.profile import UserSimpleSerializer
from cosinnus.utils.compat import atomic
from cosinnus.views.mixins.ajax import (DetailAjaxableResponseMixin,
    AjaxableFormMixin, ListAjaxableResponseMixin)
from cosinnus.views.mixins.group import RequireAdminMixin, RequireReadMixin,\
    RequireLoggedInMixin, EndlessPaginationMixin
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus.views.mixins.avatar import AvatarFormMixin
from cosinnus.core import signals
from cosinnus.core.registries.group_models import group_model_registry
from multiform.forms import InvalidArgument
from extra_views import (CreateWithInlinesView, FormSetView, InlineFormSet,
    UpdateWithInlinesView)

from cosinnus.forms.tagged import get_form  # circular import
from cosinnus.utils.urls import group_aware_reverse, get_non_cms_root_url
from cosinnus.models.tagged import BaseTagObject
from django.shortcuts import redirect, get_object_or_404
from django.http.response import Http404, HttpResponseNotAllowed
from cosinnus.utils.permissions import check_ug_admin, check_user_superuser,\
    check_object_read_access
from cosinnus.views.widget import GroupDashboard
from cosinnus.views.microsite import GroupMicrositeView
from django.views.generic.base import View
import six
from django.conf import settings
from django.core.paginator import Paginator
from cosinnus.utils.user import filter_active_users
from cosinnus.utils.functions import resolve_class
from django.views.decorators.csrf import csrf_protect

import logging
from cosinnus.templatetags.cosinnus_tags import is_superuser
from django.core.validators import validate_email
from annoying.functions import get_object_or_None
from django.contrib.auth.models import AnonymousUser
logger = logging.getLogger('cosinnus')


class SamePortalGroupMixin(object):

    def get_queryset(self):
        """
        Filter the queryset for this portal only!
        """
        return super(SamePortalGroupMixin, self).get_queryset().filter(portal=CosinnusPortal.get_current())


class CosinnusLocationInlineFormset(InlineFormSet):
    extra = 5
    max_num = 5
    form_class = CosinnusLocationForm
    model = CosinnusLocation
    
class CosinnusGroupGalleryImageInlineFormset(InlineFormSet):
    extra = 6
    max_num = 6
    form_class = CosinnusGroupGalleryImageForm
    model = CosinnusGroupGalleryImage


class CosinnusGroupFormMixin(object):
    
    model = CosinnusGroup
    # we can define additional inline formsets in settings.COSINNUS_GROUP_ADDITIONAL_INLINE_FORMSETS
    inlines = [CosinnusLocationInlineFormset, CosinnusGroupGalleryImageInlineFormset] \
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
        
        # special check: only portal admins can create groups
        if not getattr(settings, 'COSINNUS_USERS_CAN_CREATE_GROUPS', False) and self.form_view == 'add' and model_class == CosinnusSociety:
            if not (self.request.user.id in CosinnusPortal.get_current().admins or check_user_superuser(self.request.user)):
                messages.warning(self.request, _('Sorry, only portal administrators can create Groups! You can either create a Project, or write a message to one of the administrators to create a Group for you. Below you can find a listing of all administrators.'))
                return redirect(reverse('cosinnus:portal-admin-list'))
        
        return super(CosinnusGroupFormMixin, self).dispatch(*args, **kwargs)
    
    def get_form_class(self):
        
        class CosinnusGroupForm(get_form(self.group_form_class, attachable=False)):
            def dispatch_init_group(self, name, group):
                if name == 'media_tag':
                    return group
                return InvalidArgument
            
            def dispatch_init_user(self, name, user):
                if name == 'media_tag':
                    return user
                return InvalidArgument

        return CosinnusGroupForm
    
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
                deactivated_app_selection.append({
                    'app_name': app_name,
                    'app': app,
                    'label': pgettext_lazy('the_app', app),
                    'checked': app_is_active,
                    'app_not_activatable': app_not_activatable,
                })
                if app_is_active and not app_not_activatable:
                    microsite_public_apps_selection.append({
                        'app_name': app_name,
                        'app': app,
                        'label': pgettext_lazy('the_app', app),
                        'checked': app_name in microsite_public_apps,
                    })
            
        context.update({
            'group_model': self.group_model_class.__name__,
            'deactivated_app_selection': deactivated_app_selection,
            'microsite_public_apps_selection': microsite_public_apps_selection,
        })
        return context


class GroupCreateView(CosinnusGroupFormMixin, AvatarFormMixin, AjaxableFormMixin, UserFormKwargsMixin, 
                      CreateWithInlinesView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!

    form_view = 'add'
    
    message_success = _('%(team_type)s "%(group)s" was created successfully.')

    @method_decorator(membership_required)
    @atomic
    def dispatch(self, *args, **kwargs):
        return super(GroupCreateView, self).dispatch(*args, **kwargs)

    def forms_valid(self, form, inlines):
        ret = super(GroupCreateView, self).forms_valid(form, inlines)
        CosinnusGroupMembership.objects.create(user=self.request.user,
            group=self.object, status=MEMBERSHIP_ADMIN)
        messages.success(self.request, self.message_success % {'group':self.object.name, 'team_type':self.object._meta.verbose_name})
        return ret
    
    def forms_invalid(self, form, inlines):
        # workaround: on validation errors delete the entered tags
        # because taggit tags that don't exist yet cannot be rendered back properly
        # (during rendering, the then only string is attempted to be rendered as a tag-id and then not found)
        try:
            del form.forms['media_tag'].data['media_tag-tags']
        except KeyError:
            pass
        return super(GroupCreateView, self).forms_invalid(form, inlines)

    def get_context_data(self, **kwargs):
        context = super(GroupCreateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Create')
        # if we have 'group=xx' in the GET, add the parent if we are looking at a project
        if 'group' in self.request.GET and 'parent' in kwargs['form'].forms['obj']._meta.fields:
            init_parent = CosinnusGroup.objects.get_cached(pks=int(self.request.GET.get('group')))
            kwargs['form'].forms['obj'].initial['parent'] = init_parent
            kwargs['form'].forms['obj'].fields['parent'].initial = init_parent
        return context

    def get_form_kwargs(self):
        kwargs = super(GroupCreateView, self).get_form_kwargs()
        kwargs['group'] = self.object
        return kwargs
    
    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.object})

group_create = GroupCreateView.as_view()
group_create_api = GroupCreateView.as_view(is_ajax_request_url=True)


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

group_delete = GroupDeleteView.as_view()
group_delete_api = GroupDeleteView.as_view(is_ajax_request_url=True)


class GroupDetailView(SamePortalGroupMixin, DetailAjaxableResponseMixin, RequireReadMixin,
                      DetailView):

    template_name = 'cosinnus/group/group_detail.html'
    serializer_class = GroupSimpleSerializer
    
    # how many regular users are shown on the page. the rest are omitted unless ?show=all is sent
    default_num_members_shown = 25

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        admin_ids = CosinnusGroupMembership.objects.get_admins(group=self.group)
        all_member_ids = CosinnusGroupMembership.objects.get_members(group=self.group)
        pending_ids = CosinnusGroupMembership.objects.get_pendings(group=self.group)
        invited_pending_ids = CosinnusGroupMembership.objects.get_invited_pendings(group=self.group)
        
        member_ids = [id for id in all_member_ids if not id in admin_ids]
        
        # we DON'T filter for current portal here, as pending join requests can come from
        # users in other portals
        # we also exclude users who have never logged in
        _q = get_user_model().objects.all()
        _q = filter_active_users(_q)
        _q = _q.order_by('first_name', 'last_name').select_related('cosinnus_profile')
        
        admins = _q.filter(id__in=admin_ids)
        members = _q.filter(id__in=member_ids)
        pendings = _q.filter(id__in=pending_ids)
        invited = _q.filter(id__in=invited_pending_ids)
        
        # for adding members, get all users from this portal only  
        non_members =  _q.exclude(id__in=all_member_ids). \
            exclude(id__in=invited_pending_ids). \
            filter(id__in=CosinnusPortal.get_current().members)
        
        hidden_members = 0
        user_count = members.count()
        is_member_of_this_group = self.request.user.pk in admin_ids or self.request.user.pk in member_ids or \
                 check_user_superuser(self.request.user)
                 
        # for public groups if user not a member of the group, show only public users in widget
        if not self.request.user.is_authenticated():
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
            hidden_members = user_count - members.count()
        
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
        
        context.update({
            'admins': admins,
            'members': members,
            'pendings': pendings,
            'invited': invited,
            'non_members': non_members,
            'member_count': user_count,
            'hidden_user_count': hidden_members,
            'more_user_count': more_user_count,
        })
        return context

group_detail = GroupDetailView.as_view()
group_detail_api = GroupDetailView.as_view(is_ajax_request_url=True)


class GroupMembersMapListView(GroupDetailView):

    template_name = 'cosinnus/group/group_members_map.html'

group_members_map = GroupMembersMapListView.as_view()


class GroupListView(EndlessPaginationMixin, ListAjaxableResponseMixin, ListView):

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
        if settings.COSINNUS_SHOW_PRIVATE_GROUPS_FOR_ANONYMOUS_USERS or self.request.user.is_authenticated():
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
            if self.request.user.is_authenticated():
                user_pk = self.request.user.pk
                try:
                    if user_pk in CosinnusGroupMembership.objects.get_admins(group=group):
                        _admins.append(user_pk)
                    if user_pk in CosinnusGroupMembership.objects.get_members(group=group):
                        _members.append(user_pk)
                    if user_pk in CosinnusGroupMembership.objects.get_pendings(group=group):
                        _pendings.append(user_pk)
                    if user_pk in CosinnusGroupMembership.objects.get_invited_pendings(group=group):
                        _invited.append(user_pk)
                except CosinnusGroupMembership.DoesNotExist:
                    pass
            members.append(_members)
            pendings.append(_pendings)
            admins.append(_admins)
            invited.append(_invited)
            
        ctx.update({
            'rows': zip(ctx['object_list'], members, pendings, admins, invited),
            'unpaginated_rows': self.object_list,
            'map_groups': self.object_list, # unpaginated groups
            'group_type': self.group_type,
        })
        return ctx
    
group_list = GroupListView.as_view()
group_list_api = GroupListView.as_view(is_ajax_request_url=True)


class GroupListMineView(RequireLoggedInMixin, GroupListView):
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

group_list_mine = GroupListMineView.as_view()


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
    
group_list_filtered = FilteredGroupListView.as_view()



class GroupMapListView(GroupListView):
    template_name = 'cosinnus/group/group_list_map.html'

group_list_map = GroupMapListView.as_view()

class GroupUpdateView(SamePortalGroupMixin, CosinnusGroupFormMixin, AvatarFormMixin, AjaxableFormMixin, UserFormKwargsMixin,
                      RequireAdminMixin, UpdateWithInlinesView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!
    
    form_view = 'edit'
    
    message_success = _('The %(team_type)s was changed successfully.')
    
    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupUpdateView, self).get_context_data(**kwargs)
        context.update({
            'submit_label': _('Save'),
            'group': self.group}
        )
        return context
    
    def get_form_kwargs(self):
        kwargs = super(GroupUpdateView, self).get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs
    
    def forms_valid(self, form, inlines):
        messages.success(self.request, self.message_success % {'team_type':self.object._meta.verbose_name})
        return super(GroupUpdateView, self).forms_valid(form, inlines)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group})

group_update = GroupUpdateView.as_view()
group_update_api = GroupUpdateView.as_view(is_ajax_request_url=True)


class GroupUserListView(ListAjaxableResponseMixin, RequireReadMixin, ListView):

    serializer_class = UserSimpleSerializer
    template_name = 'cosinnus/group/group_user_list.html'

    def get_queryset(self):
        return self.group.users.all()

group_user_list = GroupUserListView.as_view()
group_user_list_api = GroupUserListView.as_view(is_ajax_request_url=True)



class GroupConfirmMixin(object):
    model = CosinnusGroup
    slug_url_kwarg = 'group'
    success_url = reverse_lazy('cosinnus:group-list')
    
    def get(self, *args, **kwargs):
        """ We make the allowance to call this by GET if called with ?direct=1 param,
            so that user joins can be automated with a direct link (like after being recruited) """
        if not self.request.GET.get('direct', None) == '1':
            messages.error(self.request, _('This action is not available directly!'))
            return redirect(group_aware_reverse('cosinnus:group-detail', kwargs=kwargs))
        else:
            return self.post(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.confirm_action()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def confirm_action(self):
        raise NotImplementedError()


class GroupUserJoinView(SamePortalGroupMixin, GroupConfirmMixin, DetailView):

    message_success = _('You have requested to join the %(team_type)s “%(team_name)s”. You will receive an email as soon as a team administrator responds to your request.')
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserJoinView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.referer = request.META.get('HTTP_REFERER', reverse('cosinnus:group-list'))
        return super(GroupUserJoinView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer
    
    def confirm_action(self):
        # default membership status is pending, so if we are already pending or a member, nothing happens,
        # and if we have no relation to the group, a new pending membership is created.
        try:
            m = CosinnusGroupMembership.objects.get(
                user=self.request.user,
                group=self.object,
            )
            # if member was already invited when asking to join, make him a member immediately
            if m.status == MEMBERSHIP_INVITED_PENDING:
                m.status = MEMBERSHIP_MEMBER
                m.save()
                messages.success(self.request, _('You had already been invited to "%(team_name)s" and have now been made a member immediately!') % {'team_name': self.object.name})
                signals.user_group_invitation_accepted.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
        except CosinnusGroupMembership.DoesNotExist:
            CosinnusGroupMembership.objects.create(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_PENDING
            )
            signals.user_group_join_requested.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
            messages.success(self.request, self.message_success % {'team_name': self.object.name, 'team_type':self.object._meta.verbose_name})
        self.referer = self.object.get_absolute_url()
        

group_user_join = GroupUserJoinView.as_view()


class GroupUserLeaveView(SamePortalGroupMixin, GroupConfirmMixin, DetailView):

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
        
        admins = CosinnusGroupMembership.objects.get_admins(group=self.object)
        if len(admins) > 1 or self.request.user.pk not in admins:
            try:
                membership = CosinnusGroupMembership.objects.get(
                    user=self.request.user,
                    group=self.object,
                    status=MEMBERSHIP_MEMBER if self.request.user.pk not in admins else MEMBERSHIP_ADMIN
                )
                membership.delete()
            except CosinnusGroupMembership.DoesNotExist:
                self._had_error = True
        else:
            self._had_error = True
            messages.error(self.request,
                _('You cannot leave this %(team_type)s. You are the only administrator left.') % { 'team_type':self.object._meta.verbose_name}
            )

group_user_leave = GroupUserLeaveView.as_view()


class GroupUserWithdrawView(SamePortalGroupMixin, GroupConfirmMixin, DetailView):

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
            membership = CosinnusGroupMembership.objects.get(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_PENDING
            )
            membership.delete()
        except CosinnusGroupMembership.DoesNotExist:
            self._had_error = True

group_user_withdraw = GroupUserWithdrawView.as_view()


class GroupUserInvitationDeclineView(GroupUserWithdrawView):

    message_success = _('Your invitation to %(team_type)s “%(team_name)s” was declined successfully.')
    
    def confirm_action(self):
        try:
            membership = CosinnusGroupMembership.objects.get(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_INVITED_PENDING
            )
            membership.delete()
            signals.user_group_invitation_declined.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
        except CosinnusGroupMembership.DoesNotExist:
            self._had_error = True

group_user_invitation_decline = GroupUserInvitationDeclineView.as_view()


class GroupUserInvitationAcceptView(GroupUserWithdrawView):

    message_success = _('You are now a member of %(team_type)s “%(team_name)s”. Welcome!')
    
    def confirm_action(self):
        try:
            membership = CosinnusGroupMembership.objects.get(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_INVITED_PENDING
            )
            membership.status = MEMBERSHIP_MEMBER
            membership.save()
            signals.user_group_invitation_accepted.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
        except CosinnusGroupMembership.DoesNotExist:
            self._had_error = True

group_user_invitation_accept = GroupUserInvitationAcceptView.as_view()


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
    
    template_name = 'cosinnus/group/group_detail.html'
    
    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        try:
            m = self.model.objects.get(user=user, group=self.group)
            # if the user has already requested a join when we try to invite him, accept him immediately
            if m.status == MEMBERSHIP_PENDING:
                m.status = MEMBERSHIP_MEMBER
                m.save()
                signals.user_group_join_accepted.send(sender=self, group=self.group, user=user)
                messages.success(self.request, _('User %(username)s had already requested membership and has now been made a member immediately!') % {'username': user.get_full_name()})
                # trigger signal for accepting that user's join request
            return HttpResponseRedirect(self.get_success_url())
        except self.model.DoesNotExist:
            ret = super(GroupUserInviteView, self).form_valid(form)
            signals.user_group_invited.send(sender=self, group=self.object.group, user=user)
            messages.success(self.request, _('User %(username)s was successfully invited!') % {'username': user.get_full_name()})
            return ret

    def get_user_qs(self):
        uids = self.model.objects.get_members(group=self.group)
        return get_user_model()._default_manager.exclude(id__in=uids)

group_user_add = GroupUserInviteView.as_view()
group_user_add_api = GroupUserInviteView.as_view(is_ajax_request_url=True)


class GroupUserUpdateView(AjaxableFormMixin, RequireAdminMixin,
                          UserSelectMixin, UpdateView):

    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        self.object = self.get_object()
        current_status = self.object.status
        new_status = form.cleaned_data.get('status')
        
        if (len(self.group.admins) > 1 or not self.group.is_admin(user)):
            if user != self.request.user or check_user_superuser(self.request.user):
                if current_status == MEMBERSHIP_PENDING and new_status == MEMBERSHIP_MEMBER:
                    signals.user_group_join_accepted.send(sender=self, group=self.object.group, user=user)
                return super(GroupUserUpdateView, self).form_valid(form)
            else:
                messages.error(self.request, _('You cannot change your own admin status.'))
        elif current_status == MEMBERSHIP_ADMIN and new_status != MEMBERSHIP_ADMIN:
            messages.error(self.request, _('You cannot remove “%(username)s” form '
                'this team. Only one admin left.') % {'username': user.username})
        return HttpResponseRedirect(self.get_success_url())

    def get_user_qs(self):
        return self.group.users

group_user_update = GroupUserUpdateView.as_view()
group_user_update_api = GroupUserUpdateView.as_view(is_ajax_request_url=True)


class GroupUserDeleteView(AjaxableFormMixin, RequireAdminMixin,
                          UserSelectMixin, DeleteView):

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        group = self.object.group
        user = self.object.user
        current_status = self.object.status
        if (len(group.admins) > 1 or not group.is_admin(user)):
            if user != self.request.user or check_user_superuser(self.request.user):
                self.object.delete()
                
            else:
                messages.error(self.request, _('You cannot remove yourself from a %(team_type)s.') % {'team_type':self.object._meta.verbose_name})
                return HttpResponseRedirect(self.get_success_url())
        else:
            messages.error(self.request, _('You cannot remove "%(username)s" form '
                'this team. Only one admin left.') % {'username': user.get_full_name()})
            return HttpResponseRedirect(self.get_success_url())
        
        if current_status == MEMBERSHIP_PENDING:
            signals.user_group_join_declined.send(sender=self, group=group, user=user)
            messages.success(self.request, _('Your join request was withdrawn from %(team_type)s "%(team_name)s" successfully.') % {'team_type':self.object._meta.verbose_name, 'team_name': group.name})
        if current_status == MEMBERSHIP_INVITED_PENDING:
            messages.success(self.request, _('Your invitation to user "%(username)s" was withdrawn successfully.') % {'username': user.get_full_name()})
        if current_status == MEMBERSHIP_MEMBER:
            messages.success(self.request, _('User "%(username)s" is no longer a member.') % {'username': user.get_full_name()})
        return HttpResponseRedirect(self.get_success_url())

group_user_delete = GroupUserDeleteView.as_view()
group_user_delete_api = GroupUserDeleteView.as_view(is_ajax_request_url=True)


class GroupExportView(SamePortalGroupMixin, RequireAdminMixin, TemplateView):

    template_name = 'cosinnus/group/group_export.html'

    def get_context_data(self, **kwargs):
        export_apps = []
        for app, name, label in app_registry.items():
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

group_export = GroupExportView.as_view()


class ActivateOrDeactivateGroupView(TemplateView):
    
    template_name = 'cosinnus/group/group_activate_or_deactivate.html'
    
    message_success_activate = _('%(team_name)s was re-activated successfully!')
    message_success_deactivate = _('%(team_name)s was deactivated successfully!')
    
    def dispatch(self, request, *args, **kwargs):
        group_id = int(kwargs.pop('group_id'))
        self.activate = kwargs.pop('activate')
        group = get_object_or_404(CosinnusGroup, id=group_id)
        is_admin = check_user_superuser(request.user)
        
        # only admins and group admins may deactivate groups/projects
        if not (is_admin or check_ug_admin(request.user, group)):
            redirect_to_403(request, self)
        # only admins and portal admins may deactivate CosinnusSocieties
        if group.type == CosinnusGroup.TYPE_SOCIETY:
            if not is_admin:
                messages.warning(self.request, _('Sorry, only portal administrators can deactivate Groups! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.'))
                return redirect(reverse('cosinnus:portal-admin-list'))
        
        if group.is_active and self.activate or (not group.is_active and not self.activate):
            if self.activate:
                messages.warning(self.request, _('This project/group is already active!'))
            else:
                messages.warning(self.request, _('This project/group is already inactive!'))
            return redirect(get_non_cms_root_url())
            
        self.group = group
        return super(ActivateOrDeactivateGroupView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.group.is_active = self.activate
        self.group.save() 
        # no clearing cache necessary as save() handles it
        if self.activate:
            messages.success(request, self.message_success_activate % {'team_name': self.group.name})
            return redirect(self.group.get_absolute_url())
        else:
            messages.success(request, self.message_success_deactivate % {'team_name': self.group.name})
            return redirect(get_non_cms_root_url())
    
    def get_context_data(self, **kwargs):
        context = super(ActivateOrDeactivateGroupView, self).get_context_data(**kwargs)
        context.update({
            'target_group': self.group,
            'activate': self.activate,
        })
        return context
    
activate_or_deactivate = ActivateOrDeactivateGroupView.as_view()


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
        
        if not request.user.is_authenticated():
            return True
        if not check_object_read_access(self.group, request.user):
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
            return True
        return False
    
    @dispatch_group_access()
    def dispatch(self, request, *args, **kwargs):
        redirect_result = self.check_redirect_to_microsite(request)
        if isinstance(redirect_result, six.string_types):
            return redirect(redirect_result)
        elif redirect_result:
            return self.microsite_view(request, *args, **kwargs)
        else:
            return self.dashboard_view(request, *args, **kwargs)

group_startpage = GroupStartpage.as_view()


@csrf_protect
def group_user_recruit(request, group): 
    MAXIMUM_EMAILS = 10
    
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
    user = request.user
    redirect_url = request.META.get('HTTP_REFERER', group_aware_reverse('cosinnus:group-detail', kwargs={'group': group}))
    
    # do permission checking using has_write_access(request.user, group)
    if not is_superuser(user) or not user.id in group.members:
        logger.error('Permission error when trying to recruit users!', 
             extra={'user': request.user, 'request': request, 'path': request.path, 'group_slug': group})
        messages.error(request, _('Only group/project members have permission to do this!'))
        return redirect(redirect_url)
    
    invalid = []
    existing = []
    success = []
    
    # format and validate emails
    emails = emails.replace(';', ',').replace('\n', ',').replace('\r', ',').split(',')
    for email in emails:
        # stop after 10 fragments to prevent malicious overloading
        if len(invalid) + len(existing) + len(success) > MAXIMUM_EMAILS:
            break
        
        email = email.strip(' \t\n\r')
        if not email:
            continue
        try:
            validate_email(email)
        except ValidationError:
            invalid.append(email)
            continue
        # from here on, we have a real email. check if a user with that email exists
        if get_object_or_None(get_user_model(), email=email):
            existing.append(email) 
        else:
            success.append(email)
    
    # send emails as notification signal
    virtual_users = []
    for email in success:
        virtual_user = AnonymousUser()
        virtual_user.email = email
        virtual_users.append(virtual_user)
    signals.user_group_recruited.send(sender=user, obj=group, user=user, audience=virtual_users)
    
    if invalid:
        messages.error(request, _("Sorry, these did not seem to be valid email addresses: %s") % ', '.join(invalid))
    if existing:
        messages.success(request, _("Good news! The people with these addresses already have a registered user account: %s") % ', '.join(existing))
    if success:
        messages.success(request, _("Success! We are now sending out invitations to these email addresses: %s") % ', '.join(success))
        
    return redirect(redirect_url)
    