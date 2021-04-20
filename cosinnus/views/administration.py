# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic.list import ListView
from cosinnus.utils.permissions import check_user_superuser
from django.core.exceptions import PermissionDenied
from django.views.generic.base import TemplateView
from cosinnus.forms.administration import (UserWelcomeEmailForm,
NewsletterForManagedTagsForm, UserAdminForm, NewsletterForGroupsForm)
from cosinnus.models.group import CosinnusPortal, CosinnusGroupMembership
from cosinnus.models.newsletter import Newsletter, GroupsNewsletter
from django.urls.base import reverse
from cosinnus.views.user import _send_user_welcome_email_if_enabled
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

from cosinnus.views.profile import UserProfileUpdateView
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.permissions import check_user_can_receive_emails
from cosinnus.utils.html import render_html_with_variables
from cosinnus.core.mail import send_html_mail_threaded
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment
from cosinnus.views.user import email_first_login_token_to_user
from cosinnus.conf import settings
from cosinnus.models.profile import PROFILE_SETTING_LOGIN_TOKEN_SENT
from threading import Thread
from cosinnus.views.mixins.group import RequireSuperuserMixin
from cosinnus.models.group_extra import CosinnusConference
from cosinnus.models.conference import CosinnusConferenceSettings,\
    CosinnusConferenceRoom
from django.utils.timezone import now
from _collections import defaultdict


class AdministrationView(TemplateView):
    
    template_name = 'cosinnus/administration/administration.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super(AdministrationView, self).dispatch(request, *args, **kwargs)

administration = AdministrationView.as_view()


class UserWelcomeEmailEditView(FormView):
    
    form_class = UserWelcomeEmailForm
    template_name = 'cosinnus/administration/welcome_email.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        self.portal = CosinnusPortal.get_current()
        if request.GET.get('send_test', False) == '1':
            _send_user_welcome_email_if_enabled(self.request.user, force=True)
            messages.success(self.request, _('Test email sent!'))
            return redirect(self.get_success_url())
        return super(UserWelcomeEmailEditView, self).dispatch(request, *args, **kwargs)
    
    def get_initial(self, *args, **kwargs):
        initial = super(UserWelcomeEmailEditView, self).get_initial(*args, **kwargs)
        initial.update({
            'is_active': self.portal.welcome_email_active,
            'email_text': self.portal.welcome_email_text,
        })
        return initial
    
    def get_context_data(self, *args, **kwargs):
        context = super(UserWelcomeEmailEditView, self).get_context_data(*args, **kwargs)
        context.update({
            'email_text': render_html_with_variables(self.request.user, self.portal.welcome_email_text),
        })
        return context
    
    def form_valid(self, form):
        self.form = form
        self.portal.welcome_email_active = form.cleaned_data.get('is_active', False)
        self.portal.welcome_email_text = form.cleaned_data.get('email_text', '')
        self.portal.save(update_fields=['welcome_email_active', 'welcome_email_text'])
        return super(UserWelcomeEmailEditView, self).form_valid(form)
    
    def get_success_url(self):
        return reverse('cosinnus:administration-welcome-email')
    

welcome_email_edit = UserWelcomeEmailEditView.as_view()


class NewsletterMixin(object):

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(f'cosinnus:administration-{self.url_fragment}-newsletter-update',args=(self.object.id,))


class ManagedTagsNewsletterMixin(NewsletterMixin):
    
    url_fragment = 'managed-tags'
    form_class = NewsletterForManagedTagsForm
    model = Newsletter

class GroupsNewsletterMixin(NewsletterMixin):
    
    url_fragment = 'groups'
    form_class = NewsletterForGroupsForm
    model = GroupsNewsletter


class BaseNewsletterUpdateView(UpdateView):
    
    pk_url_kwarg = 'newsletter_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['receipients'] = self._filter_valid_recipients(self._get_recipients_from_choices())
        return context

    def _get_recipients_from_choices(self):
        """ Stub for the extending views, should return the recipients depending on
            tags/groups selected """
        pass
    
    def _filter_valid_recipients(self, users):
        filtered_users = []
        for user in users:
            if settings.COSINNUS_NEWSLETTER_SENDING_IGNORES_NOTIFICATION_SETTINGS and user.is_active and user.password:
                filtered_users.append(user)
            elif (check_user_can_receive_emails(user)):
                # if the newsletter opt-in is enabled, only send the newsletter to users
                # who have the option enabled in their profiles
                if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN and not \
                        user.cosinnus_profile.settings.get('newsletter_opt_in', False):
                    continue
                filtered_users.append(user)
        return filtered_users
    
    def _send_newsletter(self, recipients):
        subject = self.object.subject
        text = self.object.body
        for recipient in recipients:
            user_text = textfield(render_html_with_variables(recipient, text))
            # omitt the topic line after "Hello user," by passing topic_instead_of_subject=' '
            send_html_mail_threaded(recipient, subject, user_text, topic_instead_of_subject=' ')

    def form_valid(self, form):
        self.object = form.save()
        if 'send_newsletter' in self.request.POST:
            recipients = self._get_recipients_from_choices()
            recipients = self._filter_valid_recipients(recipients)
            self._send_newsletter(recipients)
            self.object.sent = timezone.now()
            self.object.save()
            messages.add_message(self.request, messages.SUCCESS, _('Newsletter sent.'))
        elif 'send_test_mail' in self.request.POST:
            self._send_newsletter([self.request.user])
            messages.add_message(self.request, messages.SUCCESS, _('Test email sent.'))
        elif 'copy_newsletter' in self.request.POST:
            self.object = self._copy_newsletter()
            messages.add_message(self.request, messages.SUCCESS, _('Newsletter has been copied.'))
        else:
            messages.add_message(self.request, messages.SUCCESS, _('Newsletter has been updated.'))
        return HttpResponseRedirect(self.get_success_url())


class ManagedTagsNewsletterListView(ManagedTagsNewsletterMixin, ListView):
    template_name = 'cosinnus/administration/managed_tags_newsletter_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-sent')

managed_tags_newsletters = ManagedTagsNewsletterListView.as_view()


class ManagedTagsNewsletterCreateView(SuccessMessageMixin,
                                     ManagedTagsNewsletterMixin,
                                     CreateView):

    template_name = 'cosinnus/administration/managed_tags_newsletter_form.html'
    success_message = _("Newsletter successfully created!")


managed_tags_newsletter_create = ManagedTagsNewsletterCreateView.as_view()


class ManagedTagsNewsletterUpdateView(ManagedTagsNewsletterMixin, BaseNewsletterUpdateView):
    
    template_name = 'cosinnus/administration/managed_tags_newsletter_form.html'

    def _get_recipients_from_choices(self):
        tags = self.object.managed_tags.all()
        assignments = CosinnusManagedTagAssignment.objects.filter(managed_tag__in=tags)
        
        group_type = ContentType.objects.get(
            app_label='cosinnus', model='cosinnusgroup')
        profile_type = ContentType.objects.get(
            app_label='cosinnus', model='userprofile')
        group_ids = assignments.filter(
            content_type=group_type).values_list('object_id', flat=True)
        profile_ids = assignments.filter(
            content_type=profile_type).values_list('object_id', flat=True)
        
        tag_users = get_user_model().objects.filter(
            Q(cosinnus_groups__id__in=group_ids) | Q(cosinnus_profile__id__in=profile_ids)).distinct()
        return tag_users
    
    def _copy_newsletter(self):
        subject = '{} (copy)'.format(self.object.subject)
        body = self.object.body
        copy = self.model.objects.create(
            subject=subject,
            body=body
        )
        for managed_tag in self.object.managed_tags.all():
            copy.managed_tags.add(managed_tag)
        return copy


managed_tags_newsletter_update = ManagedTagsNewsletterUpdateView.as_view()


class GroupsNewsletterListView(GroupsNewsletterMixin, ListView):
    template_name = 'cosinnus/administration/groups_newsletter_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-sent')

groups_newsletters = GroupsNewsletterListView.as_view()


class GroupsNewsletterCreateView(SuccessMessageMixin,
                                     GroupsNewsletterMixin,
                                     CreateView):

    template_name = 'cosinnus/administration/groups_newsletter_form.html'
    success_message = _("Newsletter successfully created!")


groups_newsletter_create = GroupsNewsletterCreateView.as_view()


class GroupsNewsletterUpdateView(GroupsNewsletterMixin, BaseNewsletterUpdateView):
    
    template_name = 'cosinnus/administration/groups_newsletter_form.html'

    def _get_recipients_from_choices(self):
        groups = self.object.groups.all()
        member_dict = CosinnusGroupMembership.objects.get_members(groups=groups)
        member_ids = list(set([user_id for sub_list in member_dict.values() for user_id in sub_list]))
        users = get_user_model().objects.filter(id__in=member_ids)
        return users
    
    def _copy_newsletter(self):
        subject = '{} (copy)'.format(self.object.subject)
        body = self.object.body
        copy = self.model.objects.create(
            subject=subject,
            body=body
        )
        for group in self.object.groups.all():
            copy.groups.add(group)
        return copy

groups_newsletter_update = GroupsNewsletterUpdateView.as_view()


class UserListView(ListView):
    model = get_user_model()
    template_name = 'cosinnus/administration/user_list.html'
    ordering = '-date_joined'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

    def send_login_token(self, user):
        email_first_login_token_to_user(user)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get('search'):
            search_string = self.request.GET.get('search')
            qs = qs.filter(Q(email__icontains=search_string) |
                           Q(first_name__icontains=search_string) |
                           Q(last_name__icontains=search_string) )
        return qs

    def get_context_data(self):
        context = super().get_context_data()
        context['total'] = self.get_queryset().count()
        return context


    def post(self, request, *args, **kwargs):
        search_string = ''
        if 'search' in self.request.POST and request.POST.get('search'):
            search_string = '?search={}'.format(request.POST.get('search'))
        if 'send_login_token' in self.request.POST:
            if self.request.POST.get('send_login_token') == '__all__':
                non_tokened_users = get_user_model().objects.\
                                        filter(last_login__isnull=True).\
                                        filter(Q(password__isnull=True) | Q(password__exact=''))
                view = self
                class UserLoginTokenThread(Thread):
                    def run(self):
                        for user in non_tokened_users:
                            # avoid sending duplicate mails when two users click at the same time
                            profile = user.cosinnus_profile
                            profile.refresh_from_db()
                            if not PROFILE_SETTING_LOGIN_TOKEN_SENT in profile.settings:
                                view.send_login_token(user)
                UserLoginTokenThread().start()
                
                msg = _('Login tokens to all previously uninvited users are now being sent in the background. You can refresh this page to update the status display of invitations.')
                messages.add_message(self.request, messages.SUCCESS, msg)
            else:
                user_id = self.request.POST.get('send_login_token')
                user = get_user_model().objects.get(id=user_id)
                self.send_login_token(user)
                messages.add_message(self.request, messages.SUCCESS, _('Login token was sent to %(email)s.') % {'email': user.email})
        redirect_path = '{}{}'.format(request.path_info, search_string)
        return HttpResponseRedirect(redirect_path)

user_list = UserListView.as_view()

class AdminUserUpdateView(UserProfileUpdateView):
    template_name = 'cosinnus/administration/user_update_form.html'
    message_success = _('Die Änderungen wurden erfolgreich gespeichert.')
    
    is_admin_elevated_view = True
    disable_conditional_field_locking = True

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, *args, **kwargs):
        form = super(AdminUserUpdateView, self).get_form(*args, **kwargs)
        for field_name in form.forms['obj'].fields:
            field = form.forms['obj'].fields[field_name]
            field.required = False
        return form

    def post(self, request, *args, **kwargs):
        if 'send_login_token' in self.request.POST:
            user_id = self.request.POST.get('send_login_token')
            user = get_user_model().objects.get(id=user_id)
            email_first_login_token_to_user(user)
            messages.add_message(self.request, messages.SUCCESS, _('Login token was sent.'))
            return HttpResponseRedirect(request.path_info)
        else:
            return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(AdminUserUpdateView, self).get_form_kwargs(*args, **kwargs)
        form_kwargs.update({
            'obj__hidden_dynamic_fields_shown': True,
            'obj__readonly_dynamic_fields_enabled': True,
            'obj__user_admin_form_managed_tag_enabled': True,
        })
        return form_kwargs

user_update = AdminUserUpdateView.as_view()


class UserCreateView(SuccessMessageMixin, CreateView):
    model = get_user_model()
    form_class = UserAdminForm
    template_name = 'cosinnus/administration/user_create_form.html'
    success_url = reverse_lazy('cosinnus:administration-users')
    success_message = _("User successfully created!")

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

user_add = UserCreateView.as_view()


class ConferenceOverviewView(RequireSuperuserMixin, TemplateView):
    """ A deep-down report list view of all conferences, their rooms, events, 
        and for all of those, their `CosinnusConferenceSettings` if they have one assigned.
        
        Kwargs:
            - only_nonstandard: if True, only objects with a set `CosinnusConferenceSettings` 
                will be listed
    """
    
    template_name = 'cosinnus/administration/conference_overview.html'
    only_nonstandard = False
    past = False
    
    def dispatch(self, request, *args, **kwargs):
        self.only_nonstandard = kwargs.pop('only_nonstandard', self.only_nonstandard)
        self.past = request.GET.get('past', self.past)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        """ Gather all conferences, and their rooms and those rooms' events and for each of those,
            their conference setting object, if one exists.
            If self.only_nonstandard view option is set, we only show items if they have a conference setting item,
            otherwise we list all of them.
         """
        context = super(ConferenceOverviewView, self).get_context_data(*args, **kwargs)
        
        # split conferences by soonest running first, then list all finished ones
        conferences = CosinnusConference.objects.all_in_portal()\
                        .order_by('from_date')\
                        .prefetch_related('rooms', 'rooms__events')
        filtered_conferences = None
        if self.past: 
            filtered_conferences = conferences.exclude(to_date__gte=now())
        else:
            filtered_conferences = conferences.filter(to_date__gte=now())
        
        # make a cached list for conference settings
        all_settings = CosinnusConferenceSettings.objects.all()
        conference_settings_dict = defaultdict(dict)
        for sett in all_settings:
            conference_settings_dict[sett.content_type_id][sett.object_id] = sett
        conference_ct_id = ContentType.objects.get_for_model(CosinnusConference).id
        room_ct_id = ContentType.objects.get_for_model(CosinnusConferenceRoom).id
        from cosinnus_event.models import ConferenceEvent # noqa
        event_ct_id = ContentType.objects.get_for_model(ConferenceEvent).id
        
        conference_report_list = []
        for conference in filtered_conferences:
            # traverse the conference, its rooms and events and attach their settings to themselves
            confsetting = conference_settings_dict.get(conference_ct_id, {}).get(conference.id, None)
            setattr(conference, 'resolved_conference_setting', confsetting)
            anysetting_conference = bool(confsetting)
            
            # gather for rooms in conference
            total_rooms = 0
            total_events = 0
            rooms_and_events = []
            anysetting_rooms = False
            for room in conference.rooms.all():
                total_rooms += 1
                roomsetting = conference_settings_dict.get(room_ct_id, {}).get(room.id, None)
                setattr(room, 'resolved_conference_setting', roomsetting)
                anysetting_rooms = anysetting_rooms or bool(roomsetting)
                
                # gather for events in room
                events = []
                anysetting_events = False
                for event in room.events.all():
                    if event.is_break:
                        continue
                    total_events += 1
                    eventsetting = conference_settings_dict.get(event_ct_id, {}).get(event.id, None)
                    anysetting_events = anysetting_events or bool(eventsetting)
                    setattr(event, 'resolved_conference_setting', eventsetting)
                    if eventsetting or not self.only_nonstandard:
                        events.append(event)
                
                anysetting_rooms = anysetting_rooms or anysetting_events
                if anysetting_rooms or not self.only_nonstandard:
                    # don't append the room if it doesn't have a setting in nonstandard mode
                    if not roomsetting and self.only_nonstandard:
                        room = None
                    rooms_and_events.append((room, events))
                    
            # in the non-standard only list, we only show conferences where at least one setting was set *anywhere*
            anysetting_conference = anysetting_conference or anysetting_rooms
            if anysetting_conference or not self.only_nonstandard:
                conf_dict = {
                    'conference': conference,
                    'rooms_and_events': rooms_and_events,
                    'room_count': total_rooms,
                    'event_count': total_events,
                }
                conference_report_list.append(conf_dict)
        
        portal = CosinnusPortal.get_current()
        context.update({
            'portal': portal,
            'portal_setting': CosinnusConferenceSettings.get_for_object(portal),
            'conference_report_list': conference_report_list,
            'only_nonstandard': self.only_nonstandard,
            'past': self.past,
        })
        return context
    

conference_overview = ConferenceOverviewView.as_view()


