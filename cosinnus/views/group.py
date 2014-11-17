# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse, reverse_lazy, NoReverseMatch
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (CreateView, DeleteView, DetailView,
    ListView, UpdateView, TemplateView)

from cosinnus.core.decorators.views import superuser_required,\
    membership_required
from cosinnus.core.registries import app_registry
from cosinnus.forms.group import MembershipForm, _CosinnusSocietyForm,\
    _CosinnusProjectForm
from cosinnus.models.group import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING, CosinnusProject,
    CosinnusSociety)
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



class CosinnusGroupFormMixin(object):
    
    def get_form_class(self):
        
        group_url_key = self.request.path.split('/')[1]
        form_class = group_model_registry.get_form(group_url_key, None)
        model_class = group_model_registry.get(group_url_key, None)
        if not form_class:
            form_class = group_model_registry.get_form_by_plural_key(group_url_key, None)
            model_class = group_model_registry.get_by_plural_key(group_url_key, None)
        self.group_model_class = model_class
        
        class CosinnusGroupForm(get_form(form_class, attachable=False)):
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
        context['group_model'] = self.group_model_class.__name__
        return context
    

class GroupCreateView(CosinnusGroupFormMixin, AvatarFormMixin, AjaxableFormMixin, UserFormKwargsMixin, 
                      CreateView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!

    model = CosinnusGroup
    template_name = 'cosinnus/group/group_form.html'
    
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
        return context

    def get_form_kwargs(self):
        kwargs = super(GroupCreateView, self).get_form_kwargs()
        kwargs['group'] = self.object
        return kwargs

    def get_success_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.object.slug})

group_create = GroupCreateView.as_view()
group_create_api = GroupCreateView.as_view(is_ajax_request_url=True)


class GroupDeleteView(AjaxableFormMixin, RequireAdminMixin, DeleteView):

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


class GroupDetailView(DetailAjaxableResponseMixin, RequireReadMixin,
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
        _q = get_user_model()._default_manager.exclude(is_active=False).order_by('first_name', 'last_name') \
                             .select_related('cosinnus_profile')
        admins = _q._clone().filter(id__in=admin_ids)
        members = _q._clone().filter(id__in=member_ids)
        pendings = _q._clone().filter(id__in=pending_ids)
        non_members =  _q._clone().exclude(id__in=member_ids)
        
        context.update({
            'admins': admins,
            'members': members,
            'pendings': pendings,
            'non_members': non_members,
        })
        return context

group_detail = GroupDetailView.as_view()
group_detail_api = GroupDetailView.as_view(is_ajax_request_url=True)


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
            return model.objects.get_cached()
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



class GroupMapListView(GroupListView):
    template_name = 'cosinnus/group/group_list_map.html'

group_list_map = GroupMapListView.as_view()

class GroupUpdateView(CosinnusGroupFormMixin, AvatarFormMixin, AjaxableFormMixin, UserFormKwargsMixin,
                      RequireAdminMixin, UpdateView):

    #form_class = 
    # Note: Form_class is set dynamically in CosinnusGroupFormMixin.get_form(), depending on what group model we have!

    model = CosinnusGroup
    template_name = 'cosinnus/group/group_form.html'
    
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
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group.slug})

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


class GroupUserJoinView(GroupConfirmMixin, DetailView):

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
        CosinnusGroupMembership.objects.create(
            user=self.request.user,
            group=self.object,
            status=MEMBERSHIP_PENDING
        )

group_user_join = GroupUserJoinView.as_view()


class GroupUserLeaveView(GroupConfirmMixin, DetailView):

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


class GroupUserWithdrawView(GroupConfirmMixin, DetailView):

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
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group.slug})


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


class GroupExportView(RequireAdminMixin, TemplateView):

    template_name = 'cosinnus/group/group_export.html'

    def get_context_data(self, **kwargs):
        export_apps = []
        for app, name, label in app_registry.items():
            try:
                url = group_aware_reverse('cosinnus:%s:export' % name,
                              kwargs={'group': self.group.slug})
            except NoReverseMatch:
                continue
            export_apps.append({'label': label, 'export_url': url})

        context = super(GroupExportView, self).get_context_data(**kwargs)
        context.update({
            'export_apps': export_apps,
        })
        return context

group_export = GroupExportView.as_view()
