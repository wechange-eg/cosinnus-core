# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import logging

from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic import (DetailView,
    ListView, TemplateView)
from django.views.generic.base import View
from django.views.generic.edit import FormView, CreateView, UpdateView,\
    DeleteView
from django.utils.dateparse import parse_datetime
import six

from cosinnus.forms.group import CosinusWorkshopParticipantCSVImportForm
from cosinnus.models.conference import CosinnusConferenceRoom,\
    CosinnusConferenceApplication, APPLICATION_ACCEPTED, APPLICATION_WAITLIST,\
    APPLICATION_STATES
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership, MEMBERSHIP_ADMIN
from cosinnus.models.membership import MEMBERSHIP_MEMBER,\
    MEMBERSHIP_INVITED_PENDING
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME
from cosinnus.models.profile import UserProfile
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.user import create_base_user
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.views.mixins.group import GroupIsConferenceMixin, FilterGroupMixin,\
    RequireAdminMixin, RequireLoggedInMixin, GroupFormKwargsMixin,\
    DipatchGroupURLMixin, RequireExtraDispatchCheckMixin
from cosinnus.views.mixins.group import RequireReadMixin, RequireWriteMixin
from cosinnus.views.profile import delete_userprofile
from cosinnus.utils.urls import group_aware_reverse, redirect_with_next
from django.db import transaction
from cosinnus.forms.conference import CosinnusConferenceRoomForm
from django.contrib.contenttypes.models import ContentType
from cosinnus.utils.permissions import check_ug_admin, check_user_superuser
from django.http.response import Http404, HttpResponseForbidden,\
    HttpResponseNotFound

from cosinnus_conference.forms import (ConferenceRemindersForm,
                                       ConferenceConfirmSendRemindersForm,
                                       ConferenceParticipationManagement,
                                       ConferenceApplicationForm,
                                       PriorityFormSet,
                                       ConferenceApplicationManagementFormSet,
                                       AsignUserToEventForm)
from cosinnus_conference.utils import send_conference_reminder
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus import cosinnus_notifications
from django.utils.functional import cached_property
import xlsxwriter
from cosinnus.utils.http import make_xlsx_response
from cosinnus.views.profile import deactivate_user_and_mark_for_deletion

logger = logging.getLogger('cosinnus')


class ConferenceTemporaryUserView(SamePortalGroupMixin, RequireWriteMixin, GroupIsConferenceMixin,
                                  RequireExtraDispatchCheckMixin, FormView):

    template_name = 'cosinnus/conference/conference_temporary_users.html'
    form_class = CosinusWorkshopParticipantCSVImportForm

    def extra_dispatch_check(self):
        if not self.group.allow_conference_temporary_users:
            messages.warning(self.request, _('This function is not enabled for this conference.'))
            return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': self.group}))

    def get_object(self, queryset=None):
        return self.group

    def get_temporary_users(self):
        temporary_users = self.group.conference_members
        return [user for user in temporary_users if user.cosinnus_profile
                and not user.cosinnus_profile.scheduled_for_deletion_at]

    def post(self, request, *args, **kwargs):

        if 'upload_file' in request.POST:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

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
            deactivate_user_and_mark_for_deletion(user)
            messages.add_message(request, messages.SUCCESS, _('Successfully removed user'))

        elif 'downloadPasswords' in request.POST:
            filename = '{}_participants_passwords'.format(
                self.group.slug)
            header = [_('Workshop username'), _('First Name'),
                      _('Last Name'), _('Email'), _('Password')]
            accounts = self.get_accounts_with_password()
            return make_xlsx_response(accounts, row_names=header,
                                      file_name=filename)

        elif 'change_password' in request.POST:
            user_id = int(request.POST.get('change_password'))
            user = get_user_model().objects.get(id=user_id)
            pwd = get_random_string()
            user.set_password(pwd)
            user.save()
            return JsonResponse(
                {
                    'email': user.email,
                    'id': user.id,
                    'password': pwd
                }
            )

        return redirect(group_aware_reverse(
            'cosinnus:conference:temporary-users',
            kwargs={'group': self.group}))

    def update_all_members_status(self, status):
        for member in self.get_temporary_users():
            member.is_active = status
            if status:
                member.last_login = None
            member.save()

    def get_accounts_with_password(self):
        accounts = []
        for member in self.get_temporary_users():
            pwd = ''
            if not member.password or not member.last_login:
                pwd = get_random_string()
                member.set_password(pwd)
                member.save()
            accounts.append([
                member.cosinnus_profile.readable_workshop_user_name,
                member.first_name,
                member.last_name,
                member.email,
                pwd
            ])
        return accounts

    def update_member_status(self, user_id, status):
        try:
            user = get_user_model().objects.get(id=user_id)
            user.is_active = status
            user.save()
            return user
        except ObjectDoesNotExist:
            pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['members'] = self.get_temporary_users()
        context['group_admins'] = CosinnusGroupMembership.objects.get_admins(group=self.group)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs

    def form_valid(self, form):
        data = form.cleaned_data.get('participants')
        self.process_data(data)
        return redirect(group_aware_reverse('cosinnus:conference:temporary-users',
                                            kwargs={'group': self.group}))

    def process_data(self, data):
        groups_list = data.get('header')
        header = data.get('header_original')
        accounts_list = []
        for row in data.get('data'):
            account = self.create_account(row, groups_list)
            accounts_list.append(account)

        return header + ['email'], accounts_list

    def get_unique_workshop_name(self, name):
        no_whitespace = name.replace(' ', '')
        unique_name = '{}_{}__{}'.format(self.group.portal.id, self.group.id, no_whitespace)
        return unique_name

    @transaction.atomic
    def create_account(self, data, groups):

        username = self.get_unique_workshop_name(data[0])
        first_name = data[1]
        last_name = data[2]
        portal_name = slugify(settings.COSINNUS_PORTAL_NAME)

        try:
            name_string = '"{}":"{}"'.format(PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME, username)
            profile = UserProfile.objects.get(
                settings__contains=name_string,
                scheduled_for_deletion_at__isnull=True
            )
            user = profile.user
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            self.create_or_update_memberships(user)
            return data + [user.email, '']
        except ObjectDoesNotExist:
            random_email = '{}@{}.de'.format(get_random_string(), portal_name)
            user = create_base_user(random_email, first_name=first_name, last_name=last_name, no_generated_password=True)

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

                unique_email = 'User{}.C{}@{}.de'.format(str(user.id), str(self.group.id), portal_name)
                user.email = unique_email
                user.is_active = False
                user.save()

                self.create_or_update_memberships(user)
                return data + [unique_email]
            else:
                return data + [_('User was not created'), '']

    def create_or_update_memberships(self, user):

        # Add user to the parent group
        membership, created = CosinnusGroupMembership.objects.get_or_create(
            group=self.group,
            user=user
        )
        if created:
            membership.status = MEMBERSHIP_MEMBER
            membership.save()


class WorkshopParticipantsDownloadView(SamePortalGroupMixin, RequireWriteMixin,
                                       GroupIsConferenceMixin, View):

    def get(self, request, *args, **kwars):
        members = self.group.conference_members

        filename = '{}_statistics'.format(self.group.slug)
        rows = []
        header = ['Workshop username', 'email', 'has logged in',
                  'last login date', 'Terms of service accepted']

        for member in members:
            if (member.cosinnus_profile and not member.cosinnus_profile.scheduled_for_deletion_at):
                profile = member.cosinnus_profile
                workshop_username = profile.readable_workshop_user_name
                email = member.email
                has_logged_in, logged_in_date = self.get_last_login(member)
                tos_accepted = 1 if profile.settings.get(
                    'tos_accepted', False) else 0
                row = [workshop_username, email, has_logged_in,
                       logged_in_date, tos_accepted]
                rows.append(row)
        return make_xlsx_response(rows, row_names=header, file_name=filename)

    def get_last_login(self, member):
        has_logged_in = 1 if member.last_login else 0
        last_login = timezone.localtime(member.last_login)
        logged_in_date = ''
        if member.last_login:
            logged_in_date = last_login.strftime("%Y-%m-%d %H:%M")

        return [has_logged_in, logged_in_date]


class WorkshopParticipantsUploadSkeletonView(SamePortalGroupMixin,
                                             RequireWriteMixin,
                                             GroupIsConferenceMixin, View):

    def get(self, request, *args, **kwars):
        filename = '{}_participants.csv'.format(self.group.slug)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            filename)

        writer = csv.writer(response)

        header = [_('Workshop username'), _('First Name'), _('Last Name')]

        writer.writerow(header)

        for i in range(5):
            row = ['' for entry in header]
            writer.writerow(row)
        return response


class ConferenceRoomManagementView(RequireAdminMixin, GroupIsConferenceMixin, ListView):
    
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


class ConferencePageView(RequireReadMixin, GroupIsConferenceMixin, TemplateView):
    
    template_name = 'cosinnus/conference/conference.html'
    
    def get(self, request, *args, **kwargs):
        # get room slug if one was in URL, else try finding the first sorted room
        # self.room can be None!
        self.room = None
        # discard the event_id kwarg, it is only for the frontend
        kwargs.pop('event_id', None)
        if not 'slug' in kwargs:
            first_room = self.group.rooms.visible().first()
            if first_room:
                return redirect(first_room.get_absolute_url())
        else:
            room_slug = kwargs.pop('slug')
            self.room = get_object_or_None(CosinnusConferenceRoom, group=self.group, slug=room_slug)
        if self.room and not self.room.is_visible:
            if not check_user_superuser(request.user) and not check_ug_admin(request.user, self.group):
                return HttpResponseForbidden()
        
        self.rooms = self.group.rooms.all()
        if self.rooms.count() == 0 and (check_ug_admin(request.user, self.group) or check_user_superuser(request.user)):
            # if no rooms have been created, redirect group admins to room management
            return redirect(group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': self.group}))
        
        return super(ConferencePageView, self).get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        # hide invisible rooms from non-admins
        if not check_ug_admin(self.request.user, self.group):
            self.rooms = self.rooms.visible()
        
        ctx = {
            'slug': self.kwargs.get('slug'), # can be None
            'group': self.group,
            'room': self.room,  # can be None
            'rooms': self.rooms,
            'events': self.room.events.all() if self.room else [],
        }
        return ctx


class ConferencePageMaintenanceView(ConferencePageView):
    
    template_name = 'cosinnus/conference/conference_page.html'
    
    def get(self, request, *args, **kwargs):
        if not check_user_superuser(self.request.user):    
            return HttpResponseForbidden()
        return super(ConferencePageMaintenanceView, self).get(request, *args, **kwargs)


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
    

class CosinnusConferenceRoomCreateView(RequireAdminMixin, CosinnusConferenceRoomFormMixin, CreateView):
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


class CosinnusConferenceRoomEditView(RequireWriteMixin, CosinnusConferenceRoomFormMixin, FilterGroupMixin, UpdateView):

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


class CosinnusConferenceRoomDeleteView(RequireWriteMixin, FilterGroupMixin, DeleteView):

    model = CosinnusConferenceRoom
    message_success = _('The room was deleted successfully.')
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return group_aware_reverse('cosinnus:conference:room-management', kwargs={'group': self.group})


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


class ConferenceRemindersView(SamePortalGroupMixin, RequireWriteMixin, GroupIsConferenceMixin, FormView):

    template_name = 'cosinnus/conference/conference_reminders.html'
    form_class = ConferenceRemindersForm
    message_success = _('Conference reminder settings have been successfully updated.')

    def get_object(self, queryset=None):
        return self.group

    def get_last_sent(self):
        extra_fields = self.group.extra_fields
        if extra_fields:
            last_sent = extra_fields.get('reminder_send_immediately_last_sent')
            if last_sent:
                return parse_datetime(last_sent)

    def get_context_data(self, **kwargs):
        kwargs['immediately_message_last_sent'] = self.get_last_sent()
        kwargs['object'] = self.group
        return super(ConferenceRemindersView, self).get_context_data(**kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.group
        return kwargs

    def form_valid(self, form):
        form.save()
        # Send test email to logged in user?
        if 'test' in form.data:
            send_conference_reminder(self.group, recipients=[self.request.user],
                                     field_name=form.data.get('test'), update_setting=False)
            messages.success(self.request, _('A test email has been sent to your email address.'))
        if 'send' in form.data:
            return HttpResponseRedirect(group_aware_reverse(
                'cosinnus:conference:confirm_send_reminder',
                kwargs={'group': self.group}))
        return super(ConferenceRemindersView, self).form_valid(form)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:conference:reminders', kwargs={'group': self.group})


class ConferenceConfirmSendRemindersView(SamePortalGroupMixin,
                                         RequireWriteMixin,
                                         GroupIsConferenceMixin,
                                         FormView):
    template_name = \
        'cosinnus/conference/conference_confirm_send_reminders.html'
    form_class = ConferenceConfirmSendRemindersForm
    message_success = _('Conference reminder settings '
                        'have been successfully updated.')

    def get_members(self):
        return self.group.actual_members

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['instance'] = self.group
        return kwargs

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        kwargs['object'] = self.group
        kwargs['members'] = self.get_members()
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        if 'send' in form.data:
            send_conference_reminder(self.group, recipients=self.get_members(),
                                     field_name='send_immediately',
                                     update_setting=False)
            messages.success(self.request,
                             _('The message was sent to all participants.'))
            form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:conference:reminders',
                                   kwargs={'group': self.group})


class ConferenceParticipationManagementView(SamePortalGroupMixin,
                                            RequireWriteMixin,
                                            GroupIsConferenceMixin,
                                            FormView):
    form_class = ConferenceParticipationManagement
    template_name = 'cosinnus/conference/conference_participation_management_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'group': self.group,
        })
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        if self.group.participation_management:
            form_kwargs['instance'] = self.group.participation_management.first()
        return form_kwargs

    def form_valid(self, form):
        if not form.instance.id:
            management = form.save(commit=False)
            management.conference = self.group
            management.save()
        else:
            form.save()
        messages.success(self.request, _('Participation configurations have been updated.'))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.group.get_absolute_url()


class ConferencePropertiesMixin(object):
    """ Common properties accessed on conferences by application-related views. """
        
    @property
    def events(self):
        from cosinnus_event.models import ConferenceEvent # noqa
        return ConferenceEvent.objects.filter(group=self.group, is_break=False)\
                .exclude(type=ConferenceEvent.TYPE_COFFEE_TABLE)\
                .order_by('from_date')

    @property
    def participation_management(self):
        return self.group.participation_management.first()


class ConferenceApplicationView(SamePortalGroupMixin,
                                RequireLoggedInMixin,
                                DipatchGroupURLMixin,
                                GroupIsConferenceMixin,
                                RequireExtraDispatchCheckMixin,
                                ConferencePropertiesMixin,
                                FormView):
    form_class = ConferenceApplicationForm
    template_name = 'cosinnus/conference/conference_application_form.html'
    
    def extra_dispatch_check(self):
        if not self.group.use_conference_applications:
            messages.warning(self.request, _('This function is not enabled for this conference.'))
            return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': self.group}))

    @property
    def application(self):
        user = self.request.user
        return self.group.conference_applications.all().filter(user=user).first()

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        if self.participation_management:
            form_kwargs['participation_management'] = self.participation_management
        if self.application:
            form_kwargs['instance'] = self.application
        return form_kwargs

    def _get_prioritydict(self, form):
        formset = PriorityFormSet(self.request.POST)
        priority_dict = {}
        if formset.is_valid():
            for form in formset.forms:
                data = form.cleaned_data
                priority_dict[data.get('event_id')] = int(data.get('priority'))
            return priority_dict
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        formset = PriorityFormSet(self.request.POST)
        if formset.is_valid():
            priorities = self._get_prioritydict(form)
            if not form.instance.id:
                application = form.save(commit=False)
                application.conference = self.group
                application.user = self.request.user
                application.priorities = priorities
                application.save()
                messages.success(self.request, _('Your application has been submitted.'))
            else:
                application = form.save()
                application.priorities = priorities
                application.save()
                messages.success(self.request, _('Your application has been updated.'))
            
            # delete any invitation on application submits
            invitation = get_object_or_None(CosinnusGroupMembership, group=self.group, user=self.request.user, status=MEMBERSHIP_INVITED_PENDING)
            if invitation:
                invitation.delete()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get(self, request, *args, **kwargs):
        if not self._applications_are_active():
            messages.error(self.request, self.participation_management.application_time_string )
        if self.application and not self.application.status == 2:
            messages.error(self.request, _('You cannot change your application anymore.') )
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        if not self._applications_are_active() or (self.application and not self.application.status == 2):
            return HttpResponseForbidden()
        if 'withdraw' in request.POST:
            self.application.delete()
            messages.success(self.request, _('Application has been withdrawn.'))
            return HttpResponseRedirect(self.get_success_url())
        else:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)


    def get_success_url(self):
        return self.group.get_absolute_url()

    def _get_initial_priorities(self):
        priorities = []
        for event in self.events:
            priority = {
                'event_id': event.id,
                'event_name': event.title
            }
            if self.application and self.application.priorities.get(str(event.id)):
                priority['priority'] = self.application.priorities.get(str(event.id))
            priorities.append(priority)
        return priorities

    def _applications_are_active(self):
        pm = self.participation_management
        if pm:
            return pm.applications_are_active
        return True

    def _user_can_edit_application(self):
        if not self.application:
            return True
        return self.application.status == 2

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self._applications_are_active() and self._user_can_edit_application():
            if self.participation_management and self.participation_management.priority_choice_enabled:
                if 'formset' in kwargs:
                    priority_formset = kwargs.pop('formset')
                else:
                    priority_formset = PriorityFormSet(
                        initial = self._get_initial_priorities()
                    )
            else:
                priority_formset = PriorityFormSet()
            context.update({
                'applications_are_active': True,
                'group': self.group,
                'participation_management': self.participation_management,
                'priority_formset': priority_formset
            })
        else:
            context.update({
                'is_active': False
            })
        return context


class ConferenceParticipationManagementApplicationsView(SamePortalGroupMixin,
                                                        RequireWriteMixin,
                                                        GroupIsConferenceMixin,
                                                        ConferencePropertiesMixin,
                                                        FormView):
    form_class = ConferenceApplicationManagementFormSet
    template_name = 'cosinnus/conference/conference_application_management_form.html'
    # for printing out what happened to what users
    _users_accepted = None # array
    _users_declined = None # array
    _users_waitlisted = None # array

    @property
    def applications(self):
        return self.group.conference_applications.exclude(status=1)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['queryset'] = self.applications
        return form_kwargs

    def _set_workshop_assignments(self):
        """ Handle tagging the conference events with the participants selected """
        from cosinnus_event.models import ConferenceEvent # noqa
        
        users = self._get_applicants_for_workshop()
        formset = AsignUserToEventForm(self.request.POST, prefix='assignment')
        for form in formset:
            form.fields['users'].choices = users

        if formset.is_valid():
            for form in formset.forms:
                data = form.cleaned_data
                event = ConferenceEvent.objects.get(id=data.get('event_id'))
                event.media_tag.persons.clear()
                users = get_user_model().objects.filter(id__in=data.get('users'))
                for user in users:
                    event.media_tag.persons.add(user)
    
    def _handle_application_changed_for_status(self, application):
        """ Performs all triggers for a given changed application (accepted, declined, etc), 
            like sending mail, creating a group membership for the conference, etc. """
        notification_kwargs = {
            'sender': self,
            'obj': application, 
            'user': self.request.user,
            'audience': [application.user],
        }
        if application.status == APPLICATION_ACCEPTED:
            # add user to conference
            if not application.user.pk in self.group.admins:
                # do not apply group membership changes to admins
                self.group.add_member_to_group(application.user, MEMBERSHIP_MEMBER)
            self._users_accepted.append(application.user)
            cosinnus_notifications.user_conference_application_accepted.send(**notification_kwargs)
        else:
            # remove/leave user out of conference
            if not application.user.pk in self.group.admins:
                # do not apply group membership changes to admins!
                self.group.remove_member_from_group(application.user)
            if application.status == APPLICATION_WAITLIST:
                self._users_waitlisted.append(application.user)
                cosinnus_notifications.user_conference_application_waitlisted.send(**notification_kwargs)
            else:
                self._users_declined.append(application.user)
                cosinnus_notifications.user_conference_application_declined.send(**notification_kwargs)
    
    def form_valid(self, form):
        self._users_accepted = []
        self._users_declined = []
        self._users_waitlisted = []
        
        for application_form in form:
            application_before = CosinnusConferenceApplication.objects.get(id=application_form.instance.id)
            application_form.save()
            if application_before.status != application_form.instance.status:
                self._handle_application_changed_for_status(application_form.instance)
        self._set_workshop_assignments()
        
        if len(self._users_accepted) > 0:
            messages.success(self.request, _('The following users were accepted and added as members: %s') % ', '.join(full_name(user) for user in self._users_accepted))
        if len(self._users_waitlisted) > 0:
            messages.success(self.request, _('The following users were put on the wait list: %s') % ', '.join(full_name(user) for user in self._users_waitlisted))
        if len(self._users_declined) > 0:
            messages.success(self.request, _('The following users were declined: %s') % ', '.join(full_name(user) for user in self._users_declined))
        
        messages.success(self.request, _('Your changes were saved.'))
        return HttpResponseRedirect(self.get_success_url())

    def _get_applicants_for_workshop(self):
        accepted_applications = self.applications
        user_list = [(application.user.id, application.user.get_full_name()) for application in accepted_applications]
        return user_list

    def _get_users_for_event(self, event):
        return list(event.media_tag.persons.all().values_list('id', flat=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = self._get_applicants_for_workshop()
        initial = [{
            'event_id': event.id,
            'event_name': event.title,
            'users': self._get_users_for_event(event)
            } for event in self.events]
        assignment_formset = AsignUserToEventForm(initial=initial, prefix='assignment')
        for form in assignment_formset:
            form.fields['users'].choices = users
        context.update({
            'assignment_formset': assignment_formset
        })

        if self.participation_management and self.participation_management.participants_limit:

            places_left = 0
            accepted_applications = self.applications.filter(status=4).count()
            if accepted_applications < self.participation_management.participants_limit:
                places_left = self.participation_management.participants_limit - accepted_applications

            context.update({
                'max_number': self.participation_management.participants_limit,
                'places_left': places_left,
                'priority_choice_enabled': self.participation_management.priority_choice_enabled,
            })
        return context

    def get_success_url(self):
        return group_aware_reverse('cosinnus:conference:participation-management-applications',
                                   kwargs={'group': self.group})


class CSVDownloadMixin(object):

    @property
    def applications(self):
        """ This view shows applications of *all* statuses """
        return self.group.conference_applications.filter(status__in=[state for state, __ in APPLICATION_STATES])\
                .order_by('created')
                
    def get(self, request, *args, **kwars):
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument'
                         '.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.get_filename())

        workbook = xlsxwriter.Workbook(response, {
            'in_memory': True,
            'strings_to_formulas': False
        })
        worksheet = workbook.add_worksheet()

        row = 0
        col = 0

        header = self.get_header()

        for item in header:
            worksheet.write(row, col, str(item))
            col += 1

        row += 1
        col = 0
        
        for application in self.applications:
            table_row = self.get_application_row(application)
            for cell in table_row:
                worksheet.write(row, col, cell)
                col += 1
            row += 1
            col = 0

        workbook.close()

        return response


class ConferenceApplicantsDetailsDownloadView(SamePortalGroupMixin,
                                                RequireWriteMixin,
                                                GroupIsConferenceMixin,
                                                CSVDownloadMixin,
                                                View):
    
    @cached_property
    def conference_options(self):
        selected_options = []
        if self.management and self.management.application_options:
            if hasattr(settings, 'COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS'):
                for option in settings.COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS:
                    if option[0] in self.management.application_options:
                        selected_options.append(option)
        return selected_options

    @cached_property
    def management(self):
        return self.group.participation_management.first()

    def get_options_strings(self):
        return ['{}: {}'.format(_('Option'), option[1]) for option in self.conference_options]

    def get_application_options(self, application):
        options = self.conference_options
        result = []
        for option in options:
            if application.options and option[0] in application.options:
                result.append('x')
            else:
                result.append('')
        return result

    @cached_property
    def conditions_check(self):
        if self.management and self.management.has_conditions:
            return 'x'
        else:
            return ''

    def get_header(self):
        header = [
            _('First Name'), 
            _('Last Name'),
            _('Motivation for applying'),
            _('Status'),
        ]
        if not 'contact_email' in settings.COSINNUS_CONFERENCE_APPLICATION_FORM_HIDDEN_FIELDS:
            header += [
                _('Contact E-Mail Address')
            ]
        if not 'contact_phone' in settings.COSINNUS_CONFERENCE_APPLICATION_FORM_HIDDEN_FIELDS:
            header += [
                _('Contact Phone Number')
            ] 
        if self.management and self.management.priority_choice_enabled:   
            header += [
                _('First Choice'),
                _('Second Choice'),
            ]
        header += self.get_extra_header() 
        header += self.get_options_strings()
        return header
    
    def get_extra_header(self):
        """ Stub for overriding view in portals """
        return []
    
    def get_application_row(self, application):
        user = application.user
        row = [
            user.first_name if user.first_name else '',
            user.last_name if user.last_name else '',
            application.information,
            str(dict(APPLICATION_STATES).get(application.status)),
        ]
        if not 'contact_email' in settings.COSINNUS_CONFERENCE_APPLICATION_FORM_HIDDEN_FIELDS:
            row += [
                application.contact_email
            ]
        if not 'contact_phone' in settings.COSINNUS_CONFERENCE_APPLICATION_FORM_HIDDEN_FIELDS:
            row += [
                application.contact_phone.as_international if application.contact_phone else ''
            ]
        if self.management and self.management.priority_choice_enabled:
            row += [
                application.first_priorities_string,
                application.second_priorities_string,
            ]
        row += self.get_extra_application_row(application) 
        row += self.get_application_options(application)
        return row
    
    def get_extra_application_row(self, application):
        """ Stub for overriding view in portals """
        return []

    def get_filename(self):
        return '{} - {}.xlsx'.format(_('List of Applicants'), self.group.slug)



conference_applicant_details_download = ConferenceApplicantsDetailsDownloadView.as_view()
conference_applications = ConferenceParticipationManagementApplicationsView.as_view()
conference_application = ConferenceApplicationView.as_view()
conference_participation_management = ConferenceParticipationManagementView.as_view()
conference_temporary_users = ConferenceTemporaryUserView.as_view()
workshop_participants_download = WorkshopParticipantsDownloadView.as_view()
workshop_participants_upload_skeleton = WorkshopParticipantsUploadSkeletonView.as_view()
conference_room_management = ConferenceRoomManagementView.as_view()
conference_page = ConferencePageView.as_view()
conference_page_maintenance = ConferencePageMaintenanceView.as_view()
conference_room_add = CosinnusConferenceRoomCreateView.as_view()
conference_room_edit = CosinnusConferenceRoomEditView.as_view()
conference_room_delete = CosinnusConferenceRoomDeleteView.as_view()
conference_reminders = ConferenceRemindersView.as_view()
conference_confirm_send_reminder = ConferenceConfirmSendRemindersView.as_view()
