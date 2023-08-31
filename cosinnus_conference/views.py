# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import logging
import requests
from urllib.parse import quote

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
from django.utils.translation import ugettext_lazy as _, pgettext_lazy, ngettext
from django.views.generic import (DetailView,
    ListView, TemplateView)
from django.views.generic.base import View
from django.views.generic.edit import FormView, CreateView, UpdateView,\
    DeleteView
from django.utils.dateparse import parse_datetime
import six
from cosinnus.core import signals
from django.db.models import Q

from cosinnus.forms.group import CosinusWorkshopParticipantCSVImportForm
from cosinnus.models.conference import CosinnusConferenceRoom,\
    CosinnusConferenceApplication, APPLICATION_ACCEPTED, APPLICATION_WAITLIST,\
    APPLICATION_STATES
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership, MEMBERSHIP_ADMIN
from cosinnus.models.managed_tags import MANAGED_TAG_LABELS
from cosinnus.models.membership import MEMBERSHIP_MEMBER,\
    MEMBERSHIP_INVITED_PENDING
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME
from cosinnus.models.profile import UserProfile
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.functions import is_number
from cosinnus.utils.user import create_base_user, filter_active_users
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.views.mixins.group import GroupIsConferenceMixin, FilterGroupMixin,\
    RequireAdminMixin, RequireLoggedInMixin, GroupFormKwargsMixin,\
    DipatchGroupURLMixin, RequireExtraDispatchCheckMixin, GroupCanAccessRecordedMeetingsMixin
from cosinnus.views.mixins.group import RequireReadMixin, RequireWriteMixin
from cosinnus.views.profile import delete_userprofile
from cosinnus.utils.urls import group_aware_reverse, redirect_with_next
from django.db import transaction
from cosinnus.forms.conference import CosinnusConferenceRoomForm
from django.contrib.contenttypes.models import ContentType
from cosinnus.utils.permissions import check_ug_admin, check_user_superuser
from cosinnus_event.models import ConferenceEventAttendanceTracking
from django.http.response import Http404, HttpResponseForbidden,\
    HttpResponseNotFound

from cosinnus_conference.forms import (CHOICE_ALL_APPLICANTS, CHOICE_ALL_MEMBERS, CHOICE_APPLICANTS_AND_MEMBERS, CHOICE_INDIVIDUAL,
                                       ConferenceRemindersForm,
                                       ConferenceConfirmSendRemindersForm,
                                       ConferenceParticipationManagement,
                                       ConferenceApplicationForm,
                                       PriorityFormSet,
                                       ConferenceApplicationManagementFormSet,
                                       AsignUserToEventForm,
                                       MotivationQuestionFormSet,
                                       MotivationAnswerFormSet,
                                       AdditionalApplicationOptionsFormSet,
                                       )
from cosinnus_conference.utils import send_conference_reminder
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus import cosinnus_notifications
from django.utils.functional import cached_property
import xlsxwriter
from cosinnus.utils.http import make_xlsx_response
from cosinnus.views.profile import deactivate_user_and_mark_for_deletion
from cosinnus.core.decorators.views import redirect_to_error_page
from cosinnus.views.mixins.formsets import JsonFieldFormsetMixin
from cosinnus.apis.bigbluebutton import BigBlueButtonAPI

logger = logging.getLogger('cosinnus')


class ConferenceTemporaryUserView(SamePortalGroupMixin, RequireWriteMixin, GroupIsConferenceMixin,
                                  RequireExtraDispatchCheckMixin, FormView):

    template_name = 'cosinnus/conference/conference_temporary_users.html'
    form_class = CosinusWorkshopParticipantCSVImportForm

    def extra_dispatch_check(self):
        if not self.group.has_premium_rights:
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

        if 'activateUsers' in request.POST:
            self.group.save()
            self.update_all_members_status(True)
            messages.add_message(request, messages.SUCCESS,
                                 _('successfully activated all user accounts.'))

        elif 'deactivateUsers' in request.POST:
            self.group.save()
            self.update_all_members_status(False)
            messages.add_message(request, messages.SUCCESS,
                                 _('successfully deactivated all user accounts.'))

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

        elif 'remove_all_members' in request.POST:
            for member in self.get_temporary_users():
                deactivate_user_and_mark_for_deletion(member)
            messages.add_message(request, messages.SUCCESS, _('Successfully removed all user'))

        elif 'downloadPasswords' in request.POST:
            filename = '{}_participants_passwords'.format(
                self.group.slug)
            header = [_('Username'), _('First Name'),
                      _('Last Name'), _('Email'), _('Password')]
            accounts = self.get_accounts_with_password()
            return make_xlsx_response(accounts, row_names=header,
                                      file_name=filename)

        elif 'change_password' in request.POST:
            user_id = int(request.POST.get('change_password'))
            user = get_user_model().objects.get(id=user_id)
            pwd = get_random_string(length=12)
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
            if not member.password:
                pwd = get_random_string(length=12)
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

    def get_blank_password_users_exist(self):
        users = self.get_temporary_users()
        for user in users:
            if not user.password:
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['members'] = self.get_temporary_users()
        context['group_admins'] = CosinnusGroupMembership.objects.get_admins(
            group=self.group)
        context['download_passwords'] = self.get_blank_password_users_exist()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs

    def get_success_message(self, accounts_created, accounts_updated):
        created_count = len(accounts_created)
        updated_count = len(accounts_updated)
        message = ''
        if accounts_created:
            message = ngettext(
                'Successfully created %(created_count)d account. ',
                'Successfully created  %(created_count)d accounts. ',
                created_count,
            ) % {
                'created_count': created_count
            }

        if updated_count:
            message = str(message) + str(_('Successfully updated accounts.'))
        return message

    def form_valid(self, form):
        data = form.cleaned_data.get('participants')
        accounts_created, accounts_updated = self.process_data(data)
        success_message = self.get_success_message(accounts_created,
                                                   accounts_updated)
        messages.add_message(
            self.request, messages.SUCCESS, success_message)
        return redirect(group_aware_reverse(
            'cosinnus:conference:temporary-users',
            kwargs={'group': self.group}))

    def process_data(self, data):
        accounts_created_list = []
        accounts_updated_list = []
        for row in data.get('data'):
            account, created = self.create_or_update_account(row)
            if created:
                accounts_created_list.append(account)
            else:
                accounts_updated_list.append(account)

        return accounts_created_list, accounts_updated_list

    def get_unique_workshop_name(self, name):
        no_whitespace = name.replace(' ', '')
        unique_name = '{}_{}__{}'.format(
            self.group.portal.id, self.group.id, no_whitespace)
        return unique_name

    def get_email_domain(self):
        if settings.COSINNUS_TEMP_USER_EMAIL_DOMAIN:
            return settings.COSINNUS_TEMP_USER_EMAIL_DOMAIN
        return '{}.de'.format(slugify(settings.COSINNUS_PORTAL_NAME))

    def create_or_update_account(self, data):

        username = self.get_unique_workshop_name(data[0])
        first_name = data[1]
        last_name = data[2]
        email_domain = self.get_email_domain()

        try:
            filter_query = {
                f'settings__{PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME}': username,
                'scheduled_for_deletion_at__isnull': True,
            }
            profile = UserProfile.objects.get(**filter_query)
            user = profile.user
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            self.create_or_update_memberships(user)
            return data + [user.email, ''], False
        except ObjectDoesNotExist:
            random_email = '{}@{}'.format(get_random_string(length=12), email_domain)
            user = create_base_user(random_email, first_name=first_name, last_name=last_name, no_generated_password=True)

            if user:
                profile = get_user_profile_model()._default_manager.get_for_user(user)
                profile.settings[PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME] = username
                profile.settings[PROFILE_SETTING_WORKSHOP_PARTICIPANT] = True
                profile.email_verified = True

                profile.add_redirect_on_next_page(
                    redirect_with_next(
                        group_aware_reverse(
                            'cosinnus:group-dashboard',
                            kwargs={'group': self.group}),
                        self.request), message=None, priority=True)
                profile.save()

                unique_email = 'User{}.C{}@{}'.format(str(user.id), str(self.group.id), email_domain)
                user.email = unique_email
                user.is_active = False
                user.save()

                self.create_or_update_memberships(user)
                return data + [unique_email], True
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
        header = ['username', 'email', 'has logged in',
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

        writer = csv.writer(response, delimiter=';')

        header = [_('Username'), _('First Name'), _('Last Name')]

        writer.writerow(header)

        for i in range(1, 4):
            id = str(i)
            row = [id, 'First Name {}'.format(id), 'Last Name {}'.format(id)]
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
        dynamic_fields = self.group.dynamic_fields
        if dynamic_fields:
            last_sent = dynamic_fields.get('reminder_send_immediately_last_sent')
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


class ConferenceRecordedMeetingsView(SamePortalGroupMixin, RequireWriteMixin, GroupCanAccessRecordedMeetingsMixin, TemplateView):
    """ A list view that retrieves the recorded BBB meetings for this conference """

    template_name = 'cosinnus/conference/conference_recorded_meetings.html'
    
    def get_recorded_meetings(self):
        self._bbb_api = BigBlueButtonAPI(source_object=self.group)
        recording_list = self._bbb_api.get_recorded_meetings(group_id=self.group.id)
        return recording_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recorded_meetings = []
        recorded_meetings_not_set_up = False
        try:
            recorded_meetings = self.get_recorded_meetings()
        except BigBlueButtonAPI.RecordingAPIServerNotSetUp:
            recorded_meetings_not_set_up = True
            
        context.update({
            'object_list': recorded_meetings,
            'object': self.group,
            'recorded_meetings_not_set_up': recorded_meetings_not_set_up,
        })
        return context


class ConferenceRecordedMeetingDeleteView(ConferenceRecordedMeetingsView):
    
    def post(self, request, *args, **kwargs):
        redirect_url = group_aware_reverse('cosinnus:conference:recorded-meetings', kwargs={'group': self.group})
        recording_id = kwargs.get('recording_id')
        try:
            recorded_meetings = self.get_recorded_meetings()
        except BigBlueButtonAPI.RecordingAPIServerNotSetUp:
            return redirect(redirect_url)
        # find the recording we want to delete in the list of recordings for this group
        # this acts as a permission check to see if the user actually should be allowed to delete it
        matching_recordings = [rec for rec in recorded_meetings if rec['id'] == recording_id]
        
        if len(matching_recordings) == 0:
            messages.error(request, _('Recording %s was not found, has already been deleted, or you do not have permission to delete it.') % recording_id)
        else:
            recording = matching_recordings[0]
            recording_name = recording['name']
            success = self._bbb_api.delete_recorded_meetings(recording_id)
            if success:
                messages.success(request, _('Recording %s was successfully deleted.') % recording_name)
            else:
                messages.error(request, _('Recording %s could not be deleted because of a server error.') % recording_name)
        return redirect(redirect_url)


class NoRecipientsDefinedException(Exception):
    """
    Workaround exception to throw in case the `Recipients` field was left empty.
    """
    pass


class NoConferenceApplicantsFoundException(Exception):
    """
    Workaround exeption to throw in case there are no pending applications found. 
    """
    pass


class ConferenceConfirmSendRemindersView(SamePortalGroupMixin,
                                         RequireWriteMixin,
                                         GroupIsConferenceMixin,
                                         FormView):
    template_name = \
        'cosinnus/conference/conference_confirm_send_reminders.html'
    form_class = ConferenceConfirmSendRemindersForm
    message_success = _('Conference reminder settings '
                        'have been successfully updated.')

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except NoRecipientsDefinedException:
            messages.error(self.request, _('Please supply one ore more recipients.'))
            return redirect(group_aware_reverse('cosinnus:conference:reminders',
                                   kwargs={'group': self.group}))
        except NoConferenceApplicantsFoundException:
            messages.error(self.request, _('No conference applicants found at the moment.'))
            return redirect(group_aware_reverse('cosinnus:conference:reminders',
                                   kwargs={'group': self.group}))

    def get_members(self):
        recipient_choice = self.group.dynamic_fields.get('reminder_recipients_choices', None)

        if recipient_choice is None or not is_number(recipient_choice):
            logger.error('Invalid value for recipients in ConferenceConfirmSendRemindersView:get_members() function', extra={'recipient_choice': recipient_choice})
            raise NoRecipientsDefinedException()
        recipient_choice = int(recipient_choice)

        # handle diverse cases in accordance with the `recipients_choices` choice field
        if recipient_choice == CHOICE_APPLICANTS_AND_MEMBERS:
            pending_application_qs = CosinnusConferenceApplication.objects.filter(conference=self.group).filter(may_be_contacted=True).pending_and_accepted()
            all_user_ids = pending_application_qs.values_list('user', flat=True)
            members_user_ids = self.group.members # covers the current members of the group incl. admins
            recipients_applicants_and_members = filter_active_users(get_user_model().objects.filter(Q(id__in=all_user_ids) | Q(id__in=members_user_ids)))
            return recipients_applicants_and_members 
        elif recipient_choice == CHOICE_ALL_APPLICANTS:
            pending_application_qs = CosinnusConferenceApplication.objects.filter(conference=self.group).filter(may_be_contacted=True).pending()
            all_user_ids = pending_application_qs.values_list('user', flat=True)
            recipients_all_applicants = filter_active_users(get_user_model().objects.filter(id__in=all_user_ids))
            if not recipients_all_applicants:
                raise NoConferenceApplicantsFoundException()
            return recipients_all_applicants
        elif recipient_choice == CHOICE_ALL_MEMBERS:
            members_qs = CosinnusConferenceApplication.objects.filter(conference=self.group).filter(may_be_contacted=True).accepted_in_past()
            all_user_ids = members_qs.values_list('user', flat=True)
            members_user_ids = self.group.members
            participants_all_members = filter_active_users(get_user_model().objects.filter(Q(id__in=all_user_ids) | Q(id__in=members_user_ids)))
            return participants_all_members
        elif recipient_choice == CHOICE_INDIVIDUAL:
            pending_application_qs = CosinnusConferenceApplication.objects.filter(conference=self.group).filter(may_be_contacted=True).pending_and_accepted()
            all_user_ids = pending_application_qs.values_list('user', flat=True)
            members_user_ids = self.group.members
            required_user_ids = self.group.dynamic_fields.get('reminder_send_immediately_users', [])
            if not required_user_ids:
                raise NoRecipientsDefinedException()
            recipients_individual = filter_active_users(get_user_model().objects.filter(id__in=required_user_ids).filter(Q(id__in=all_user_ids) | Q(id__in=members_user_ids)))
            return recipients_individual
        else:
            logger.error('Unknown choice for recipients in ConferenceConfirmSendRemindersView:get_members() function', extra={'recipient_choice': recipient_choice})
            raise NoRecipientsDefinedException()

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
            members = self.get_members()
            send_conference_reminder(self.group, recipients=members,
                                     field_name='send_immediately',
                                     update_setting=False)
            messages.success(self.request,
                             _('The message was sent to the chosen participants.'))
            form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:conference:reminders',
                                   kwargs={'group': self.group})


class ConferenceParticipationManagementView(SamePortalGroupMixin,
                                            RequireWriteMixin,
                                            GroupIsConferenceMixin,
                                            JsonFieldFormsetMixin,
                                            FormView):
    form_class = ConferenceParticipationManagement
    template_name = 'cosinnus/conference/conference_participation_management_form.html'
    json_field_formsets = {
        'motivation_questions': MotivationQuestionFormSet,
        'additional_application_options': AdditionalApplicationOptionsFormSet,
    }
    instance = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'group': self.group,
        })
        return context

    def get_instance(self):
        if self.instance:
            return self.instance
        if self.group.participation_management:
            self.instance = self.group.participation_management.first()
        return self.instance

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        instance = self.get_instance()
        if instance:
            form_kwargs['instance'] = instance
        return form_kwargs

    def form_valid(self, form):
        json_field_formsets_valid = self.json_field_formset_form_valid_hook()
        if not json_field_formsets_valid:
            return self.form_invalid(form)
        management = form.save(commit=False)
        if not form.instance.id:
            management.conference = self.group
        self.json_field_formset_pre_save_hook(management)
        management.save()
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
                                JsonFieldFormsetMixin,
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

    def get_instance(self):
        return self.application

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
        json_field_formsets_valid = self.json_field_formset_form_valid_hook()
        formset = PriorityFormSet(self.request.POST)
        if json_field_formsets_valid and formset.is_valid():
            priorities = self._get_prioritydict(form)
            if not form.instance.id:
                application = form.save(commit=False)
                application.conference = self.group
                application.user = self.request.user
                application.priorities = priorities
                self.json_field_formset_pre_save_hook(application)
                application.save()

                signals.user_group_join_requested.send(sender=self, obj=self.group, user=self.request.user, 
                    audience=list(get_user_model()._default_manager.filter(id__in=self.group.admins)))
                messages.success(self.request, _('Your application has been submitted.'))
            else:
                application = form.save()
                application.priorities = priorities
                self.json_field_formset_pre_save_hook(application)
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

    def get_json_field_formsets(self):
        formsets = {}
        if self.participation_management.information_field_enabled and self.participation_management.motivation_questions:
            formsets['motivation_answers'] = MotivationAnswerFormSet
        return formsets

    def json_field_formset_initial(self):
        return {'motivation_answers': self.participation_management.motivation_questions}

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

        if self.participation_management:
            context.update({
                'priority_choice_enabled': self.participation_management.priority_choice_enabled,
            })

            if self.participation_management.participants_limit:
                places_left = 0
                accepted_applications = self.applications.filter(status=4).count()
                if accepted_applications < self.participation_management.participants_limit:
                    places_left = self.participation_management.participants_limit - accepted_applications

                context.update({
                    'max_number': self.participation_management.participants_limit,
                    'places_left': places_left,
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
        if self.management:
            if self.management.application_options and hasattr(settings, 'COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS'):
                for option in settings.COSINNUS_CONFERENCE_PARTICIPATION_OPTIONS:
                    if option[0] in self.management.application_options:
                        selected_options.append(option)
            if self.management.additional_application_options:
                selected_options.extend(self.management.get_additional_application_options_choices())
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

    def get_motivation_question_strings(self):
        return [question.get('question', '') for question in self.management.motivation_questions]

    def get_motivation_answers(self, application):
        answers = []
        for question in self.management.motivation_questions:
            for answer in application.motivation_answers:
                if answer.get('question') == question.get('question'):
                    answers.append(answer.get('answer', ''))
        return answers

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
        ]

        if self.management.information_field_enabled and self.management.information_field_initial_text:
            header += [_('Motivation for applying')]

        header += [_('Status')]

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
        if self.management.information_field_enabled and self.management.motivation_questions:
            header += self.get_motivation_question_strings()
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
        ]

        if self.management.information_field_enabled and self.management.information_field_initial_text:
            row += [application.information]

        row += [str(dict(APPLICATION_STATES).get(application.status))]

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
        if self.management.information_field_enabled and application.motivation_answers:
            row += self.get_motivation_answers(application)
        row += self.get_application_options(application)
        return row
    
    def get_extra_application_row(self, application):
        """ Stub for overriding view in portals """
        return []

    def get_filename(self):
        return '{} - {}.xlsx'.format(_('List of Applicants'), self.group.slug)


class ConferenceAttendanceTrackingMixin:
    """ Provide conference and event info and statistics using ConferenceEventAttendanceTracking. """

    def get_event_attendance_stats(self):
        """Provides attendance stats for each conference event using ConferenceEventAttendanceTracking."""
        stats = []
        for event in self.events:
            attendance = ConferenceEventAttendanceTracking.get_attendance(self.group, event)
            event_stats = {
                'name': event.title,
                'room_type': event.get_type_verbose(),
                'duration': attendance.get('event_duration', '-'),
                'number_of_attendees': attendance.get('num_attendees'),
                'average_time_spent_per_attendee': attendance.get('avg_time_attendee'),
                'average_time_spent_per_attendee_percent': attendance.get('avg_time_attendee_percent', '-'),
            }
            stats.append(event_stats)
        return stats

    def get_conference_attendance_stats(self):
        """Provides attendance stats for the overall conference event using ConferenceEventAttendanceTracking."""
        stats = {
            'conference_name': self.group.name,
        }

        # num. invitations
        stats['number_invitations'] = len(self.group.invited_pendings) + self.group.conference_applications.count()

        # num. registrations
        stats['number_registrations'] = self.group.member_count

        # attendance
        attendance = ConferenceEventAttendanceTracking.get_attendance(self.group)
        stats.update({
            'number_of_attendees': attendance.get('num_attendees'),
            'average_time_spent_per_attendee': attendance.get('avg_time_attendee'),
        })
        return stats


class ConferenceUserDataStatisticsMixin:
    """
    Provides portal specific user data as defined in COSINNUS_CONFERENCE_STATISTICS_USER_DATA_FIELDS for the conference
    statistics.
    """

    def _get_field_value_display(self, field, value):
        """ Returns the display name of a field value if defined in choices. """
        display_value = value
        field_choices = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS[field].choices
        if field_choices:
            choices_dict = {choice[0]: choice[1] for choice in field_choices}
            if isinstance(value, list):
                display_value = [choices_dict.get(subvalue) for subvalue in value]
            else:
                display_value = choices_dict.get(value)
        return display_value

    def get_portal_specific_user_data(self):
        """ Returns a table of user data for each conference member. """

        data = []

        for user in ConferenceEventAttendanceTracking.get_attendees(self.group):
            field_data = []
            for field in settings.COSINNUS_CONFERENCE_STATISTICS_USER_DATA_FIELDS:
                if field == settings.COSINNUS_CONFERENCE_STATISTICS_USER_DATA_MANAGED_TAGS_FIELD:
                    managed_tags = user.cosinnus_profile.get_managed_tags()
                    value = managed_tags[0].name if managed_tags else None
                else:
                    value = user.cosinnus_profile.dynamic_fields.get(field, None)
                    value = self._get_field_value_display(field, value)
                if value is None or value == '':
                    value = '-'
                field_data.append(value)
            data.append(field_data)
        return data

    def get_aggregated_portal_specific_user_data(self):
        """
        Provides aggregated user data with its occurrence percentage.
        Returns a table with each line containing the aggregated user field values and the percentage as tuple.
        Example for country and organization fields: [[('DE', 50), ('UA', 25), ('-', 25)], [('WECHANGE eG', 100)]
        """
        data = self.get_portal_specific_user_data()
        aggregated_data = []
        number_of_fields = len(settings.COSINNUS_CONFERENCE_STATISTICS_USER_DATA_FIELDS)
        for field_num in range(number_of_fields):
            field_values = []
            for user_data in data:
                field_value = user_data[field_num]
                if isinstance(field_value, list):
                    field_values.extend(field_value)
                else:
                    field_values.append(field_value)
            unique_field_values = set(field_values)
            aggregated_field_data = []
            for field_value in unique_field_values:
                field_value_percent = round(field_values.count(field_value) / len(data) * 100)
                aggregated_field_data.append((field_value, field_value_percent))
            aggregated_field_data.sort(key=lambda t: t[1], reverse=True)
            aggregated_data.append(aggregated_field_data)
        return aggregated_data


class ConferenceStatisticsDashboardView(RequireWriteMixin,
                                        GroupIsConferenceMixin,
                                        ConferencePropertiesMixin,
                                        ConferenceAttendanceTrackingMixin,
                                        ConferenceUserDataStatisticsMixin,
                                        TemplateView):
    """
    Implements a simple conference statistics dashboard showing the data provided by the
    ConferenceAttendanceTrackingMixin and ConferenceUserDataStatisticsMixin as tables.
    """

    template_name = 'cosinnus/conference/conference_statistics.html'

    def get_portal_specific_user_data_labels(self):
        labels = []
        for field in settings.COSINNUS_CONFERENCE_STATISTICS_USER_DATA_FIELDS:
            if field == settings.COSINNUS_CONFERENCE_STATISTICS_USER_DATA_MANAGED_TAGS_FIELD:
                label = MANAGED_TAG_LABELS.MANAGED_TAG_NAME
            else:
                label = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS[field].label
            labels.append(label)
        return labels

    def get_dashboard_stats(self):
        stats = {}
        conference_stats = self.get_conference_attendance_stats()
        event_stats = self.get_event_attendance_stats()
        stats.update({
            'conference_stats': conference_stats,
            'event_stats': event_stats,
        })
        if settings.COSINNUS_CONFERENCE_STATISTICS_USER_DATA_FIELDS:
            user_data = self.get_aggregated_portal_specific_user_data()
            user_data_fields = self.get_portal_specific_user_data_labels()
            stats.update({
                'user_data_fields': user_data_fields,
                'user_data': user_data,
            })
        return stats

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'object': self.group,
        })
        if ConferenceEventAttendanceTracking.has_tracking(self.group):
            dashboard_stats = self.get_dashboard_stats()
            context.update(**dashboard_stats)
        else:
            messages.info(self.request, _('Attendance data is not available for this conference.'))
        return context


class ConferenceStatisticsDownloadView(RequireWriteMixin,
                                       GroupIsConferenceMixin,
                                       ConferenceAttendanceTrackingMixin,
                                       View):
    """ Provide conference statistic from the ConferenceAttendanceTrackingMixin as XLSX download. """

    def get(self, request, *args, **kwars):

        header = [
            'conference_name',
            'number_invitations',
            'number_registrations',
            'number_of_attendees',
            'average_time_spent_per_attendee'
        ]

        filename = '{}_conference_statistics'.format(self.group.slug)
        conference_stats = self.get_conference_attendance_stats()
        rows = [conference_stats.values()]
        response = make_xlsx_response(rows, row_names=header, file_name=filename)
        return response


class ConferenceEventStatisticsDownloadView(RequireWriteMixin,
                                            GroupIsConferenceMixin,
                                            ConferencePropertiesMixin,
                                            ConferenceAttendanceTrackingMixin,
                                            View):
    """ Provide conference event statistic from the ConferenceAttendanceTrackingMixin as XLSX download. """

    def get(self, request, *args, **kwars):

        header = [
            'single_event_name',
            'single_event_room_type',
            'single_event_duration_minutes',
            'single_event_number_of_attendees',
            'single_event_average_time_spent_per_attendee_minutes',
            'single_event_average_time_spent_per_attendee_percent',
        ]

        filename = '{}_conference_event_statistics'.format(self.group.slug)
        conference_event_stats = self.get_event_attendance_stats()
        rows = [event_stats.values() for event_stats in conference_event_stats]
        response = make_xlsx_response(rows, row_names=header, file_name=filename)
        return response


class ConferenceUserDataDownloadView(RequireWriteMixin,
                                     GroupIsConferenceMixin,
                                     ConferencePropertiesMixin,
                                     ConferenceUserDataStatisticsMixin,
                                     View):
    """ Provide conference user data from the ConferenceUserDataStatisticsMixin as XLSX download. """

    def get(self, request, *args, **kwars):

        header = settings.COSINNUS_CONFERENCE_STATISTICS_USER_DATA_FIELDS
        filename = '{}_conference_user_data'.format(self.group.slug)
        rows = []
        data = self.get_portal_specific_user_data()
        for data_row in data:
            row = []
            for value in data_row:
                if isinstance(value, list):
                    # convert list-values into comma-separated values
                    if len(value) > 1:
                        value = [f'"{subvalue}"' for subvalue in value]
                    # convert to string to handle translations proxies
                    value = ', '.join(str(subvalue) for subvalue in value)
                row.append(value)
            rows.append(row)


        response = make_xlsx_response(rows, row_names=header, file_name=filename)
        return response


conference_user_data_download = ConferenceUserDataDownloadView.as_view()
conference_event_statistics_download = ConferenceEventStatisticsDownloadView.as_view()
conference_statistics_download = ConferenceStatisticsDownloadView.as_view()
conference_statistics = ConferenceStatisticsDashboardView.as_view()
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
conference_recorded_meetings = ConferenceRecordedMeetingsView.as_view()
conference_recorded_meeting_delete = ConferenceRecordedMeetingDeleteView.as_view()
conference_confirm_send_reminder = ConferenceConfirmSendRemindersView.as_view()
