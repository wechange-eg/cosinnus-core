# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import logging

from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic import (DetailView,
    ListView, TemplateView)
from django.views.generic.base import View
from django.views.generic.edit import FormView, CreateView, UpdateView,\
    DeleteView
import six

from cosinnus.forms.group import CosinusWorkshopParticipantCSVImportForm
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER)
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME
from cosinnus.models.profile import UserProfile
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.user import create_base_user
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.views.mixins.group import GroupIsConferenceMixin
from cosinnus.views.mixins.group import RequireReadMixin, RequireWriteMixin
from cosinnus.views.profile import delete_userprofile
from cosinnus.utils.urls import group_aware_reverse, redirect_with_next
from django.db import transaction
from cosinnus.forms.conference import CosinnusConferenceRoomForm
from django.contrib.contenttypes.models import ContentType
from cosinnus.utils.permissions import check_ug_admin, check_user_superuser
from django.http.response import Http404, HttpResponseForbidden,\
    HttpResponseNotFound


logger = logging.getLogger('cosinnus')


class ConferenceManagementView(SamePortalGroupMixin, RequireWriteMixin, GroupIsConferenceMixin, DetailView):

    template_name = 'cosinnus/conference/conference_management.html'

    def get_object(self, queryset=None):
        return self.group

    def post(self, request, *args, **kwargs):
        if 'startConferenence' in request.POST:
            self.group.conference_is_running = True
            self.group.save()
            self.update_all_members_status(True)
            messages.add_message(request, messages.SUCCESS,
                                 _('Conference successfully started and user accounts activated'))

        elif 'finishConferenence' in request.POST:
            self.group.conference_is_running = False
            self.group.save()
            self.update_all_members_status(False)
            messages.add_message(request, messages.SUCCESS,
                                 _('Conference successfully finished and user accounts deactivated'))

        elif 'deactivate_member' in request.POST:
            user_id = int(request.POST.get('deactivate_member'))
            user = self.update_member_status(user_id, False)
            if user:
                messages.add_message(request, messages.SUCCESS, _('Successfully deactivated user account'))

        elif 'activate_member' in request.POST:
            user_id = int(request.POST.get('activate_member'))
            user = self.update_member_status(user_id, True)
            if user:
                messages.add_message(request, messages.SUCCESS, _('Successfully activated user account'))

        elif 'remove_member' in request.POST:
            user_id = int(request.POST.get('remove_member'))
            user = get_user_model().objects.get(id=user_id)
            delete_userprofile(user)
            messages.add_message(request, messages.SUCCESS, _('Successfully removed user'))

        return redirect(group_aware_reverse('cosinnus:conference:management',
                                            kwargs={'group': self.group}))

    def update_all_members_status(self, status):
        for member in self.group.conference_members:
            member.is_active = status
            if status:
                member.last_login = None
            member.save()

    def update_member_status(self, user_id, status):
        try:
            user = get_user_model().objects.get(id=user_id)
            user.is_active = status
            user.save()
            return user
        except ObjectDoesNotExist:
            pass

    def get_member_workshops(self, member):
        return CosinnusGroupMembership.objects.filter(user=member, group__parent=self.group)

    def get_members_and_workshops(self):
        members = []
        for member in self.group.conference_members:
            member_dict = {
                'member': member,
                'workshops': self.get_member_workshops(member)
            }
            members.append(member_dict)
        return members

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['members'] = self.get_members_and_workshops()
        context['group_admins'] = CosinnusGroupMembership.objects.get_admins(group=self.group)

        return context

conference_management = ConferenceManagementView.as_view()


class WorkshopParticipantsUploadView(SamePortalGroupMixin, RequireWriteMixin, GroupIsConferenceMixin, FormView):

    template_name = 'cosinnus/conference/workshop_participants_upload.html'
    form_class = CosinusWorkshopParticipantCSVImportForm

    def get_object(self, queryset=None):
        return self.group

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs

    def form_valid(self, form):
        data = form.cleaned_data.get('participants')
        header, accounts = self.process_data(data)

        filename = '{}_participants_passwords.csv'.format(self.group.slug)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        writer.writerow(header)
        for account in accounts:
            writer.writerow(account)
        return response

    def process_data(self, data):
        groups_list = data.get('header')
        header = data.get('header_original')
        accounts_list = []
        for row in data.get('data'):
            account = self.create_account(row, groups_list)
            accounts_list.append(account)

        return header + ['email', 'password'], accounts_list

    def get_unique_workshop_name(self, name):
        no_whitespace = name.replace(' ', '')
        unique_name = '{}_{}__{}'.format(self.group.portal.id, self.group.id, no_whitespace)
        return unique_name

    @transaction.atomic
    def create_account(self, data, groups):

        username = self.get_unique_workshop_name(data[0])
        first_name = data[1]
        last_name = data[2]

        try:
            name_string = '"{}":"{}"'.format(PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME, username)
            profile = UserProfile.objects.get(settings__contains=name_string)
            user = profile.user
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            self.create_or_update_memberships(user, data, groups)
            return data + [user.email, '']
        except ObjectDoesNotExist:
            random_email = '{}@wechange.de'.format(get_random_string())
            pwd = get_random_string()
            user = create_base_user(random_email, password=pwd, first_name=first_name, last_name=last_name)

            if user:
                profile = get_user_profile_model()._default_manager.get_for_user(user)
                profile.settings[PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME] = username
                profile.settings[PROFILE_SETTING_WORKSHOP_PARTICIPANT] = True
                profile.add_redirect_on_next_page(
                    redirect_with_next(
                        group_aware_reverse(
                            'cosinnus:group-dashboard',
                            kwargs={'group': self.group}),
                        self.request), message=None, priority=True)
                profile.save()

                unique_email = 'User{}.C{}@wechange.de'.format(str(user.id), str(self.group.id))
                user.email = unique_email
                user.is_active = False
                user.save()

                self.create_or_update_memberships(user, data, groups)
                return data + [unique_email, pwd]
            else:
                return data + [_('User was not created'), '']

    def create_or_update_memberships(self, user, data, groups):

        # Add user to the parent group
        membership, created = CosinnusGroupMembership.objects.get_or_create(
            group=self.group,
            user=user
        )
        if created:
            membership.status = MEMBERSHIP_MEMBER
            membership.save()

        # Add user to all child groups/projects that were marked with 1 or 2 in the csv or delete membership
        for i, group in enumerate(groups):
            if isinstance(group, CosinnusGroup):
                if data[i] in [str(MEMBERSHIP_MEMBER), str(MEMBERSHIP_ADMIN)]:
                    status = int(data[i])
                    membership, created = CosinnusGroupMembership.objects.get_or_create(
                        group=group,
                        user=user
                    )
                    if created:
                        membership.status = status
                        membership.save()
                    else:
                        current_status = membership.status
                        if current_status < status:
                            membership.status = status
                            membership.save()
                else:
                    try:
                        membership = CosinnusGroupMembership.objects.get(
                            group=group,
                            user=user
                        )
                        membership.delete()
                    except ObjectDoesNotExist:
                        continue
            else:
                continue

workshop_participants_upload = WorkshopParticipantsUploadView.as_view()


class WorkshopParticipantsDownloadView(SamePortalGroupMixin, RequireWriteMixin, GroupIsConferenceMixin, View):


    def get(self, request, *args, **kwars):
        members = self.group.conference_members

        filename = '{}_statistics.csv'.format(self.group.slug)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        header = ['Workshop username', 'email', 'workshops count', 'has logged in', 'last login date', 'Terms of service accepted']

        writer = csv.writer(response)
        writer.writerow(header)

        for member in members:
            workshop_username = member.cosinnus_profile.readable_workshop_user_name
            email = member.email
            workshop_count = self.get_membership_count(member)
            has_logged_in, logged_in_date = self.get_last_login(member)
            tos_accepted = 1 if member.cosinnus_profile.settings.get('tos_accepted', False) else 0
            row = [workshop_username, email, workshop_count, has_logged_in, logged_in_date, tos_accepted]
            writer.writerow(row)
        return response

    def get_membership_count(self, member):
        return member.cosinnus_groups.filter(parent=self.group).count()

    def get_last_login(self, member):
        has_logged_in = 1 if member.last_login else 0
        last_login = timezone.localtime(member.last_login)
        logged_in_date = last_login.strftime("%Y-%m-%d %H:%M") if member.last_login else ''

        return [has_logged_in, logged_in_date]

workshop_participants_download = WorkshopParticipantsDownloadView.as_view()


class WorkshopParticipantsUploadSkeletonView(SamePortalGroupMixin, RequireWriteMixin, GroupIsConferenceMixin, View):

    def get(self, request, *args, **kwars):
        filename = '{}_participants.csv'.format(self.group.slug)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)

        header = [_('Workshop username'), _('First Name'), _('Last Name')]
        workshop_slugs = [group.slug for group in self.group.groups.all()]

        full_header = header + workshop_slugs

        writer.writerow(full_header)

        for i in range(5):
            row = ['' for entry in full_header]
            writer.writerow(row)
        return response

workshop_participants_upload_skeleton = WorkshopParticipantsUploadSkeletonView.as_view()



class ConferenceRoomManagementView(RequireWriteMixin, GroupIsConferenceMixin, ListView):
    
    model = CosinnusConferenceRoom
    ordering = ('sort_index', 'title')
    template_name = 'cosinnus/conference/conference_room_management.html'

    def get_queryset(self):
        queryset = super(ConferenceRoomManagementView, self).get_queryset()
        queryset = queryset.filter(group=self.group)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['object'] = self.group
        return context

conference_room_management = ConferenceRoomManagementView.as_view()


class ConferencePageView(RequireReadMixin, GroupIsConferenceMixin, TemplateView):
    
    template_name = 'cosinnus/conference/conference.html'
    
    def get(self, request, *args, **kwargs):
        # get room slug if one was in URL, else try finding the first sorted room
        # self.room can be None!
        self.room = None
        if not 'slug' in kwargs:
            first_room = self.group.rooms.visible().first()
            if first_room:
                return redirect(first_room.get_absolute_url())
        else:
            room_slug = kwargs.pop('slug')
            self.room = get_object_or_None(CosinnusConferenceRoom, group=self.group, slug=room_slug)
        if self.room and not self.room.is_visible:    
            return HttpResponseForbidden()
        return super(ConferencePageView, self).get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        rooms = self.group.rooms.all()
        # hide invisible rooms from non-admins
        if not check_ug_admin(self.request.user, self.group):
            rooms = rooms.visible()
        
        ctx = {
            'slug': self.kwargs.get('slug'), # can be None
            'group': self.group,
            'room': self.room,  # can be None
            'rooms': rooms,
            'events': self.room.events.all() if self.room else [],
        }
        return ctx

conference_page = ConferencePageView.as_view()


class ConferencePageMaintenanceView(ConferencePageView):
    
    template_name = 'cosinnus/conference/conference_page.html'
    
    def get(self, request, *args, **kwargs):
        if not check_user_superuser(self.request.user):    
            return HttpResponseForbidden()
        return super(ConferencePageMaintenanceView, self).get(request, *args, **kwargs)

conference_page_maintenance = ConferencePageMaintenanceView.as_view()


class CosinnusConferenceRoomFormMixin(object):
    
    form_class = CosinnusConferenceRoomForm
    model = CosinnusConferenceRoom
    template_name = 'cosinnus/conference/conference_room_form.html'
    
    def get_form_kwargs(self):
        kwargs = super(CosinnusConferenceRoomFormMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['group'] = self.group
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusConferenceRoomFormMixin, self).get_context_data(**kwargs)
        context.update({
            'group': self.group,
        })
        return context
    

class CosinnusConferenceRoomCreateView(RequireWriteMixin, CosinnusConferenceRoomFormMixin, CreateView):
    """ Create View for CosinnusConferenceRooms """
    
    form_view = 'add'
    message_success = _('The room was created successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusConferenceRoomCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        ret = super(CosinnusConferenceRoomCreateView, self).form_valid(form)
        return ret
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': self.group})
    
conference_room_add = CosinnusConferenceRoomCreateView.as_view()


class CosinnusConferenceRoomEditView(RequireWriteMixin, CosinnusConferenceRoomFormMixin, UpdateView):

    form_view = 'edit'
    message_success = _('The room was saved successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusConferenceRoomEditView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': self.group})
    

conference_room_edit = CosinnusConferenceRoomEditView.as_view()


class CosinnusConferenceRoomDeleteView(RequireWriteMixin, DeleteView):

    model = CosinnusConferenceRoom
    message_success = _('The room was deleted successfully.')
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': self.group})

conference_room_delete = CosinnusConferenceRoomDeleteView.as_view()



class FilterConferenceRoomMixin(object):
    """
    Sets `self.room` as CosinnusConferenceRoom for the group already set during dispatch, 
    pulled from the `kwargs['room_slug']`, 404s if not found. Excepcts `self.group` to be set.
    """

    def dispatch(self, request, *args, **kwargs):
        room_slug = kwargs.pop('room_slug', None)
        if not room_slug:
            raise ImproperlyConfigured('Room slug was not set!')
        self.room = get_object_or_None(CosinnusConferenceRoom, group=self.group, slug=room_slug)
        if self.room is None:
            return HttpResponseNotFound(_('The supplied Conference Room could not be found'))
        return super(FilterConferenceRoomMixin, self).dispatch(request, *args, **kwargs)

