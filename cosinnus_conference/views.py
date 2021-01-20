# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import logging

from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic import (DetailView,
    ListView, TemplateView)
from django.views.generic.base import View
from django.views.generic.edit import FormView, CreateView, UpdateView,\
    DeleteView
import six

from cosinnus.forms.group import CosinusWorkshopParticipantCSVImportForm
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership, MEMBERSHIP_ADMIN
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT
from cosinnus.models.profile import PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME
from cosinnus.models.profile import UserProfile
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.user import create_base_user
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.views.mixins.group import GroupIsConferenceMixin, FilterGroupMixin,\
    RequireAdminMixin
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
                                       ConferenceParticipationManagement,
                                       ConferenceApplicationForm,
                                       PriorityFormSet,
                                       ApplicationFormSet,
                                       AsignUserToEventForm)
from cosinnus_conference.utils import send_conference_reminder
from cosinnus_event.models import Event

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

    def get_context_data(self, **kwargs):
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
            send_conference_reminder(conference=self.group, recipients=[self.request.user],
                                     field_name=form.data.get('test'), update_setting=False)
            messages.success(self.request, _('A test email has been sent to your email address.'))
        return super(ConferenceRemindersView, self).form_valid(form)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:conference:reminders', kwargs={'group': self.group})


class ConferenceParticipationManagementView(SamePortalGroupMixin,
                                            RequireWriteMixin,
                                            GroupIsConferenceMixin,
                                            FormView):
    form_class = ConferenceParticipationManagement
    template_name = 'cosinnus/conference/conference_participation_management.html'

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
        return group_aware_reverse('cosinnus:conference:participation-management',
                                   kwargs={'group': self.group})


class ConferenceApplicationView(SamePortalGroupMixin,
                                RequireReadMixin,
                                GroupIsConferenceMixin,
                                FormView):
    form_class = ConferenceApplicationForm
    template_name = 'cosinnus/conference/conference_application.html'

    @property
    def events(self):
        return Event.objects.filter(group=self.group).order_by('id')

    @property
    def participation_management(self):
        return self.group.participation_management.first()

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
                messages.success(self.request, _('Application has been sent.'))
            else:
                application = form.save()
                application.priorities = priorities
                application.save()
                messages.success(self.request, _('Application has been updated.'))
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get(self, request, *args, **kwargs):
        if not self._is_active():
            messages.error(self.request, self.participation_management.application_time_string )
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        if not self._is_active():
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
        return group_aware_reverse('cosinnus:group-microsite',
                                   kwargs={'group': self.group})

    def _get_initial_priorities(self):
        if not self.application:
            return [{'event_id': event.id,
                     'event_name': event.title} for event in self.events]
        else:
            return [{'event_id': event.id,
                     'event_name': event.title,
                     'priority' : self.application.priorities.get(str(event.id))}
                     for event in self.events]

    def _is_active(self):
        pm = self.participation_management
        if pm:
            return pm.is_active
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self._is_active():
            if 'formset' in kwargs:
                priority_formset = kwargs.pop('formset')
            else:
                priority_formset = PriorityFormSet(
                    initial = self._get_initial_priorities()
                )
            context.update({
                'is_active': True,
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
                                                        FormView):
    form_class = ApplicationFormSet
    template_name = 'cosinnus/conference/conference_participation_management_applications.html'

    @property
    def participation_management(self):
        return self.group.participation_management.first()

    @property
    def events(self):
        return Event.objects.filter(group=self.group).order_by('id')

    @property
    def applications(self):
        return self.group.conference_applications.all()

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['queryset'] = self.applications
        return form_kwargs

    def _set_workshop_assignments(self):
        users = self._get_applicants_for_workshop()
        formset = AsignUserToEventForm(self.request.POST, prefix='assignment')
        for form in formset:
            form.fields['users'].choices = users

        if formset.is_valid():
            for form in formset.forms:
                data = form.cleaned_data
                event = Event.objects.get(id=data.get('event_id'))
                event.media_tag.persons.clear()
                users = get_user_model().objects.filter(id__in=data.get('users'))
                for user in users:
                    event.media_tag.persons.add(user)

    def form_valid(self, form):
        for application in form:
            application.save()
        self._set_workshop_assignments()
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
            'places_left': places_left
            })
        return context

    def get_success_url(self):
        return group_aware_reverse('cosinnus:conference:participation-management-applications',
                                   kwargs={'group': self.group})


conference_participation_management_applications = ConferenceParticipationManagementApplicationsView.as_view()
conference_application = ConferenceApplicationView.as_view()
conference_participation_management = ConferenceParticipationManagementView.as_view()
conference_management = ConferenceManagementView.as_view()
workshop_participants_upload = WorkshopParticipantsUploadView.as_view()
workshop_participants_download = WorkshopParticipantsDownloadView.as_view()
workshop_participants_upload_skeleton = WorkshopParticipantsUploadSkeletonView.as_view()
conference_room_management = ConferenceRoomManagementView.as_view()
conference_page = ConferencePageView.as_view()
conference_page_maintenance = ConferencePageMaintenanceView.as_view()
conference_room_add = CosinnusConferenceRoomCreateView.as_view()
conference_room_edit = CosinnusConferenceRoomEditView.as_view()
conference_room_delete = CosinnusConferenceRoomDeleteView.as_view()
conference_reminders = ConferenceRemindersView.as_view()
