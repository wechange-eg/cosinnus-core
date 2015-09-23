# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import chain

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse, reverse_lazy, NoReverseMatch
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic import (CreateView, DeleteView, DetailView,
    ListView, UpdateView, TemplateView)

from cosinnus.core.decorators.views import membership_required, redirect_to_403
from cosinnus.core.registries import app_registry
from cosinnus.forms.group import MembershipForm
from cosinnus.models.group import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING, CosinnusProject,
    CosinnusSociety, CosinnusPortal)
from cosinnus.models.serializers.group import GroupSimpleSerializer
from cosinnus.models.serializers.profile import UserSimpleSerializer
from cosinnus.utils.compat import atomic
from cosinnus.views.mixins.ajax import (DetailAjaxableResponseMixin,
    AjaxableFormMixin, ListAjaxableResponseMixin)
from cosinnus.views.mixins.group import RequireAdminMixin, RequireReadMixin
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus.views.mixins.avatar import AvatarFormMixin
from cosinnus.core import signals
from cosinnus.core.registries.group_models import group_model_registry
from multiform.forms import InvalidArgument

from cosinnus.forms.tagged import get_form  # circular import
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.models.tagged import BaseTagObject
from django.shortcuts import redirect, get_object_or_404
from django.http.response import Http404
from django.db.models import Q
from cosinnus.templatetags.cosinnus_tags import is_group_admin
from cosinnus.utils.permissions import check_ug_admin, check_user_portal_admin


class SamePortalGroupMixin(object):

    def get_queryset(self):
        """
        Filter the queryset for this portal only!
        """
        return super(SamePortalGroupMixin, self).get_queryset().filter(portal=CosinnusPortal.get_current())

class CosinnusGroupFormMixin(object):
    
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
        if self.form_view == 'add' and model_class == CosinnusSociety:
            if not (self.request.user.id in CosinnusPortal.get_current().admins or self.request.user.is_superuser):
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
        
        deactivated_app_selection = []
        for app_name in app_registry: # eg 'cosinnus_todo'
            # label for the checkbox is the app identifier translation
            app = app_name.split('_')[-1] # eg 'todo'
            # filter for cosinnus app being deactivatable
            if app_registry.is_deactivatable(app_name):
                deactivated_app_selection.append({
                    'app_name': app_name,
                    'app': app,
                    'label': pgettext_lazy('the_app', app),
                    'checked': True if (not self.object or not self.object.deactivated_apps) else app_name not in deactivated_apps,
                })
            
        context.update({
            'group_model': self.group_model_class.__name__,
            'deactivated_app_selection': deactivated_app_selection,
        })
        return context
    

class GroupCreateView(CosinnusGroupFormMixin, AvatarFormMixin, AjaxableFormMixin, UserFormKwargsMixin, 
                      CreateView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!

    model = CosinnusGroup
    template_name = 'cosinnus/group/group_form.html'
    form_view = 'add'
    
    message_success = _('%(group_type)s "%(group)s" was created successfully.')

    @method_decorator(membership_required)
    @atomic
    def dispatch(self, *args, **kwargs):
        return super(GroupCreateView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        ret = super(GroupCreateView, self).form_valid(form)
        CosinnusGroupMembership.objects.create(user=self.request.user,
            group=self.object, status=MEMBERSHIP_ADMIN)
        messages.success(self.request, self.message_success % {'group':self.object.name, 'group_type':self.object._meta.verbose_name})
        return ret
    
    def form_invalid(self, form):
        # workaround: on validation errors delete the entered tags
        # because taggit tags that don't exist yet cannot be rendered back properly
        # (during rendering, the then only string is attempted to be rendered as a tag-id and then not found)
        try:
            del form.forms['media_tag'].data['media_tag-tags']
        except KeyError:
            pass
        return super(GroupCreateView, self).form_invalid(form)

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

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        admin_ids = CosinnusGroupMembership.objects.get_admins(group=self.group)
        member_ids = CosinnusGroupMembership.objects.get_members(group=self.group)
        pending_ids = CosinnusGroupMembership.objects.get_pendings(group=self.group)
        
        # we DON'T filter for current portal here, as pending join requests can come from
        # users in other portals
        _q = get_user_model()._default_manager.exclude(is_active=False) \
                             .order_by('first_name', 'last_name') \
                             .select_related('cosinnus_profile')
        admins = _q._clone().filter(id__in=admin_ids)
        members = _q._clone().filter(id__in=member_ids)
        pendings = _q._clone().filter(id__in=pending_ids)
        # for adding members, get all users from this portal only  
        non_members =  _q._clone().exclude(id__in=member_ids). \
            filter(id__in=CosinnusPortal.get_current().members)
        
        hidden_members = 0
        user_count = members.count()
        # for public groups if user not a member of the group, show only public users in widget
        if not self.request.user.is_authenticated() or not \
                (self.request.user.pk in admin_ids or self.request.user.pk in member_ids):
            # admins are always visible in this view, because a they should be contactable
            members = members.filter(cosinnus_profile__media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
            pendings = pendings.filter(cosinnus_profile__media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
            # concatenate admins into members, because we might have sorted out a private admin, 
            # and the template iterates only over members to display people
            members = list(set(chain(members, admins)))
            hidden_members = user_count - len(members)
            
        context.update({
            'admins': admins,
            'members': members,
            'pendings': pendings,
            'non_members': non_members,
            'member_count': user_count,
            'hidden_user_count': hidden_members,
        })
        return context

group_detail = GroupDetailView.as_view()
group_detail_api = GroupDetailView.as_view(is_ajax_request_url=True)


class GroupMembersMapListView(GroupDetailView):

    template_name = 'cosinnus/group/group_members_map.html'

group_members_map = GroupMembersMapListView.as_view()


class GroupListView(ListAjaxableResponseMixin, ListView):

    model = CosinnusGroup
    template_name = 'cosinnus/group/group_list.html'
    serializer_class = GroupSimpleSerializer
    
    def get_queryset(self):
        group_plural_url_key = self.request.path.split('/')[1]
        group_class = group_model_registry.get_by_plural_key(group_plural_url_key, None)
        self.group_type = group_class.GROUP_MODEL_TYPE
        
        model = group_class or self.model
        if self.request.user.is_authenticated():
            # special case for the group-list: we can see inactive groups here that we are an admin of
            regular_groups = model.objects.get_cached()
            my_inactive_groups = model.objects.filter(portal_id=CosinnusPortal.get_current().id, is_active=False)
            if not (self.request.user.is_superuser or check_user_portal_admin(self.request.user)):
                # filter for groups user is admin of if he isnt a superuser
                my_inactive_groups = my_inactive_groups.filter(id__in=model.objects.get_for_user_group_admin_pks(self.request.user, includeInactive=True))
            my_inactive_groups = list(my_inactive_groups)
            return regular_groups + my_inactive_groups
        else:
            return list(model.objects.public())

    def get_context_data(self, **kwargs):
        ctx = super(GroupListView, self).get_context_data(**kwargs)
        members, pendings, admins = [], [], []
        
        # for each group, put the user pk in the appropriate status list if the user is in the group
        # for this view, we do not care about other users, thus the reduced query
        for group in ctx['object_list']:
            _members, _pendings, _admins = [], [], []
            if self.request.user.is_authenticated():
                user_pk = self.request.user.pk
                try:
                    membership = CosinnusGroupMembership.objects.get(group=group, user__id=user_pk)
                    if membership.status == MEMBERSHIP_ADMIN:
                        _admins.append(user_pk)
                    if membership.status == MEMBERSHIP_MEMBER or membership.status == MEMBERSHIP_ADMIN:
                        _members.append(user_pk)
                    if membership.status == MEMBERSHIP_PENDING:
                        _pendings.append(user_pk)
                except CosinnusGroupMembership.DoesNotExist:
                    pass
            members.append(_members)
            pendings.append(_pendings)
            admins.append(_admins)
            
        ctx.update({
            'rows': zip(self.object_list, members, pendings, admins),
            'group_type': self.group_type,
        })
        return ctx
    
group_list = GroupListView.as_view()
group_list_api = GroupListView.as_view(is_ajax_request_url=True)


class ProjectListView(GroupListView):
    model = CosinnusProject

project_list = ProjectListView.as_view()

class SocietyListView(GroupListView):
    model = CosinnusSociety

society_list = SocietyListView.as_view()


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
                      RequireAdminMixin, UpdateView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!

    model = CosinnusGroup
    template_name = 'cosinnus/group/group_form.html'
    form_view = 'edit'
    
    message_success = _('The %(group_type)s was changed successfully.')
    
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
    
    def form_valid(self, form):
        messages.success(self.request, self.message_success % {'group_type':self.object._meta.verbose_name})
        return super(GroupUpdateView, self).form_valid(form)

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

    def get_context_data(self, **kwargs):
        context = super(GroupConfirmMixin, self).get_context_data(**kwargs)
        context.update({
            'confirm_label': self.get_confirm_label(),
            'confirm_question': self.get_confirm_question(),
            'confirm_title': self.get_confirm_title(),
            'submit_css_classes': getattr(self, 'submit_css_classes', None)
        })
        return context

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

    def get_confirm_label(self):
        return self.confirm_label

    def get_confirm_question(self):
        return self.confirm_question % {'group_name': self.object.name, 'group_type':self.object._meta.verbose_name}

    def get_confirm_title(self):
        return self.confirm_title % {'group_name': self.object.name, 'group_type':self.object._meta.verbose_name}


class GroupUserJoinView(SamePortalGroupMixin, GroupConfirmMixin, DetailView):

    confirm_label = _('Join')
    confirm_question = _('Do you want to join the %(group_type)s “%(group_name)s”?')
    confirm_title = _('Join %(group_type)s “%(group_name)s”?')
    message_success = _('You have requested to join the %(group_type)s “%(group_name)s”. You will receive an email as soon as a group administrator responds to your request.')
    
    template_name = 'cosinnus/group/group_confirm.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserJoinView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.referer = request.META.get('HTTP_REFERER', reverse('cosinnus:group-list'))
        return super(GroupUserJoinView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        signals.user_group_join_requested.send(sender=self, obj=self.object, user=self.request.user, audience=list(get_user_model()._default_manager.filter(id__in=self.object.admins)))
        messages.success(self.request, self.message_success % {'group_name': self.object.name, 'group_type':self.object._meta.verbose_name})
        return self.referer
    
    def confirm_action(self):
        # default membership status is pending, so if we are already pending or a member, nothing happens,
        # and if we have no relation to the group, a new pending membership is created.
        CosinnusGroupMembership.objects.get_or_create(
            user=self.request.user,
            group=self.object
        )

group_user_join = GroupUserJoinView.as_view()


class GroupUserLeaveView(SamePortalGroupMixin, GroupConfirmMixin, DetailView):

    confirm_label = _('Leave')
    confirm_question = _('Do you want to leave the %(group_type)s “%(group_name)s”?')
    confirm_title = _('Leaving %(group_type)s “%(group_name)s”?')
    submit_css_classes = 'btn-danger'
    message_success = _('You are no longer a member of the %(group_type)s “%(group_name)s”.')
    
    template_name = 'cosinnus/group/group_confirm.html'

    @method_decorator(login_required)
    @atomic
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserLeaveView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.referer = request.META.get('HTTP_REFERER', reverse('cosinnus:group-list'))
        return super(GroupUserLeaveView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        messages.success(self.request, self.message_success % {'group_name': self.object.name, 'group_type':self.object._meta.verbose_name})
        return self.referer
    
    def confirm_action(self):
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
                print ">>> error!"
        else:
            messages.error(self.request,
                _('You cannot leave this %(group_type)s. You are the only administrator left.') % { 'group_type':self.object._meta.verbose_name}
            )

group_user_leave = GroupUserLeaveView.as_view()


class GroupUserWithdrawView(SamePortalGroupMixin, GroupConfirmMixin, DetailView):

    confirm_label = _('Withdraw')
    confirm_question = _('Do you want to withdraw your join request to the %(group_type)s “%(group_name)s”?')
    confirm_title = _('Withdraw join request to %(group_type)s “%(group_name)s”?')
    submit_css_classes = 'btn-danger'
    message_success = _('Your join request was withdrawn from %(group_type)s “%(group_name)s” successfully.')
    
    template_name = 'cosinnus/group/group_confirm.html'

    @method_decorator(login_required)
    @atomic
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserWithdrawView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.referer = request.META.get('HTTP_REFERER', reverse('cosinnus:group-list'))
        return super(GroupUserWithdrawView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        messages.success(self.request, self.message_success % {'group_name': self.object.name, 'group_type':self.object._meta.verbose_name})
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
            pass

group_user_withdraw = GroupUserWithdrawView.as_view()


class UserSelectMixin(object):

    form_class = MembershipForm
    model = CosinnusGroupMembership
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
    template_name = 'cosinnus/group/group_user_form.html'

    @atomic
    def dispatch(self, request, *args, **kwargs):
        return super(UserSelectMixin, self).dispatch(request, *args, **kwargs)

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


class GroupUserAddView(AjaxableFormMixin, RequireAdminMixin, UserSelectMixin,
                       CreateView):

    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        status = form.cleaned_data.get('status')
        try:
            m = self.model.objects.get(user=user, group=self.group)
            m.status = status
            m.save(update_fields=['status'])
            return HttpResponseRedirect(self.get_success_url())
        except self.model.DoesNotExist:
            return super(GroupUserAddView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(GroupUserAddView, self).get_context_data(**kwargs)
        context.update({
            'submit_label': _('Add'),
        })
        return context

    def get_user_qs(self):
        uids = self.model.objects.get_members(group=self.group)
        return get_user_model()._default_manager.exclude(id__in=uids)

group_user_add = GroupUserAddView.as_view()
group_user_add_api = GroupUserAddView.as_view(is_ajax_request_url=True)


class GroupUserUpdateView(AjaxableFormMixin, RequireAdminMixin,
                          UserSelectMixin, UpdateView):

    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        self.object = self.get_object()
        current_status = self.object.status
        new_status = form.cleaned_data.get('status')
        
        if (len(self.group.admins) > 1 or not self.group.is_admin(user)):
            if user != self.request.user or self.request.user.is_superuser:
                if current_status == MEMBERSHIP_PENDING and new_status == MEMBERSHIP_MEMBER:
                    signals.user_group_join_accepted.send(sender=self, group=self.object.group, user=user)
                return super(GroupUserUpdateView, self).form_valid(form)
            else:
                messages.error(self.request, _('You cannot change your own admin status.'))
        elif current_status == MEMBERSHIP_ADMIN and new_status != MEMBERSHIP_ADMIN:
            messages.error(self.request, _('You cannot remove “%(username)s” form '
                'this group. Only one admin left.') % {'username': user.username})
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(GroupUserUpdateView, self).get_context_data(**kwargs)
        context.update({
            'submit_label': _('Save'),
        })
        return context

    def get_user_qs(self):
        return self.group.users

group_user_update = GroupUserUpdateView.as_view()
group_user_update_api = GroupUserUpdateView.as_view(is_ajax_request_url=True)


class GroupUserDeleteView(AjaxableFormMixin, RequireAdminMixin,
                          UserSelectMixin, DeleteView):

    template_name = 'cosinnus/group/group_confirm.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        group = self.object.group
        user = self.object.user
        current_status = self.object.status
        if (len(group.admins) > 1 or not group.is_admin(user)):
            if user != self.request.user or self.request.user.is_superuser:
                self.object.delete()
            else:
                messages.error(self.request, _('You cannot remove yourself from a %(group_type)s.') % {'group_type':self.object._meta.verbose_name})
        else:
            messages.error(self.request, _('You cannot remove “%(username)s” form '
                'this group. Only one admin left.') % {'username': user.username})
        if current_status == MEMBERSHIP_PENDING:
            signals.user_group_join_declined.send(sender=self, group=group, user=user)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(GroupUserDeleteView, self).get_context_data(**kwargs)
        group_name = self.object.group.name
        context.update({
            'confirm_label': _('Delete'),
            'confirm_question': _('Do you want to remove the user “%(username)s”  from the %(group_type)s “%(group_name)s”?') % {
                'username': self.object.user.get_username(),
                'group_name': group_name,
                'group_type':self.object._meta.verbose_name,
            },
            'confirm_title': _('Remove user from %(group_type)s “%(group_name)s”?') % {
                'group_name': group_name,
                'group_type':self.object._meta.verbose_name,
            },
            'submit_css_classes': 'btn-danger',
        })
        return context

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
    
    message_success_activate = _('%(group_name)s was re-activated successfully!')
    message_success_deactivate = _('%(group_name)s was deactivated successfully!')
    
    def dispatch(self, request, *args, **kwargs):
        group_id = int(kwargs.pop('group_id'))
        self.activate = kwargs.pop('activate')
        group = get_object_or_404(CosinnusGroup, id=group_id)
        is_portal_admin = check_user_portal_admin(self.request.user)
        
        # only admins and group admins may deactivate groups/projects
        if not (request.user.is_superuser or check_ug_admin(request.user, group) or is_portal_admin):
            redirect_to_403(request, self)
        # only admins and portal admins may deactivate CosinnusSocieties
        if group.type == CosinnusGroup.TYPE_SOCIETY:
            if not is_portal_admin:
                messages.warning(self.request, _('Sorry, only portal administrators can deactivate Groups! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.'))
                return redirect(reverse('cosinnus:portal-admin-list'))
        
        if group.is_active and self.activate or (not group.is_active and not self.activate):
            if self.activate:
                messages.warning(self.request, _('This project/group is already active!'))
            else:
                messages.warning(self.request, _('This project/group is already inactive!'))
            return redirect(reverse('cosinnus:user-dashboard'))
            
        self.group = group
        return super(ActivateOrDeactivateGroupView, self).dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.group.is_active = self.activate
        self.group.save() 
        # no clearing cache necessary as save() handles it
        if self.activate:
            messages.success(request, self.message_success_activate % {'group_name': self.group.name})
            return redirect(self.group.get_absolute_url())
        else:
            messages.success(request, self.message_success_deactivate % {'group_name': self.group.name})
            return redirect(reverse('cosinnus:user-dashboard'))
    
    def get_context_data(self, **kwargs):
        context = super(ActivateOrDeactivateGroupView, self).get_context_data(**kwargs)
        context.update({
            'target_group': self.group,
            'activate': self.activate,
        })
        return context
    
activate_or_deactivate = ActivateOrDeactivateGroupView.as_view()
