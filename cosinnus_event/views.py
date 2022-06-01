# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from collections import defaultdict
import dateutil.parser
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseNotAllowed
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import DeleteView, UpdateView, CreateView
from django.views.generic.list import ListView
from django.utils.timezone import now, localtime
from django import forms

from extra_views import (CreateWithInlinesView, FormSetView, InlineFormSetFactory,
    UpdateWithInlinesView)

from django_ical.views import ICalFeed

from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
    GroupFormKwargsMixin, FilterGroupMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus.views.attached_object import AttachableViewMixin

from cosinnus_event.conf import settings
from cosinnus_event.forms import EventForm, SuggestionForm, VoteForm,\
    EventNoFieldForm, CommentForm, DoodleForm, ConferenceEventLobbyForm,\
    ConferenceEventStageForm, ConferenceEventWorkshopForm,\
    ConferenceEventDiscussionForm, ConferenceEventCoffeeTableForm
from cosinnus_event.models import Event, Suggestion, Vote, upcoming_event_filter,\
    past_event_filter, Comment, EventAttendance, ConferenceEvent
from django.shortcuts import get_object_or_404, redirect
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_event.filters import EventFilter
from cosinnus.utils.urls import group_aware_reverse, redirect_next_or
from cosinnus.utils.permissions import check_object_read_access,\
    filter_tagged_object_queryset_for_user
from cosinnus.core.decorators.views import require_user_token_access, dispatch_group_access, get_group_for_request,\
    redirect_to_403
from django.contrib.sites.shortcuts import get_current_site
from cosinnus.utils.functions import ensure_list_of_ints, unique_aware_slugify, is_number
from cosinnus.utils.group import get_cosinnus_group_model
from django.views.decorators.csrf import csrf_protect
from django.http.response import HttpResponseBadRequest
from annoying.functions import get_object_or_None
from cosinnus.views.mixins.reflected_objects import ReflectedObjectSelectMixin,\
    MixReflectedObjectsMixin, ReflectedObjectRedirectNoticeMixin
from cosinnus.utils.permissions import check_object_write_access

import logging
from django.utils.encoding import force_text
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.contrib.auth.models import AnonymousUser
from datetime import timedelta
from cosinnus.views.common import DeleteElementView, apply_likefollowstar_object
from cosinnus.views.mixins.tagged import EditViewWatchChangesMixin,\
    RecordLastVisitedMixin
from cosinnus_event import cosinnus_notifications
from django.contrib.auth import get_user_model
from ajax_forms.ajax_forms import AjaxFormsCreateViewMixin,\
    AjaxFormsCommentCreateViewMixin, AjaxFormsDeleteViewMixin
from uuid import uuid1
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import ensure_group_type
from cosinnus_conference.views import FilterConferenceRoomMixin
logger = logging.getLogger('cosinnus')


class EventIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:event:list', kwargs={'group': self.group})


class EventListView(RequireReadMixin, CosinnusFilterMixin, MixReflectedObjectsMixin, FilterGroupMixin, ListView):

    model = Event
    filterset_class = EventFilter
    event_view = 'upcoming'
    show_past_events = getattr(settings, 'COSINNUS_EVENT_CALENDAR_ALSO_SHOWS_PAST_EVENTS', True)
    
    def get_queryset(self):
        """ In the calendar we only show scheduled events """
        qs = self.get_future_queryset()
        self.queryset = qs
        return qs
    
    def get_base_queryset(self):
        if hasattr(self, 'base_queryset'):
            return self.base_queryset
        self.queryset = None # reset self.queryset to get a base queryset, not an overloaded one
        qs = super(EventListView, self).get_queryset()
        
        if settings.COSINNUS_EVENT_EVENTS_GROUP_SHOWS_ALL_PUBLIC_EVENTS and \
                self.group.slug and self.group.slug == getattr(settings, 'NEWW_EVENTS_GROUP_SLUG', None):
            # mix in public qs
            public_qs = Event.objects.public().filter(group__portal=self.group.portal)
            qs = (qs | public_qs).distinct()
        self.base_queryset = qs
        
        return self.base_queryset
        
    def get_future_queryset(self):
        qs = self.get_base_queryset()
        qs = qs.filter(state=Event.STATE_SCHEDULED)
        if not self.show_past_events:
            qs = upcoming_event_filter(qs)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(EventListView, self).get_context_data(**kwargs)
        doodle_count = self.get_base_queryset().filter(state=Event.STATE_VOTING_OPEN).count()
        future_events = self.get_queryset()
        future_events_count = future_events.count()
        proxy_events = future_events.filter(is_hidden_group_proxy=True)
        proxy_event_count = proxy_events.count()
        
        context.update({
            'future_events': future_events,
            'future_events_count': future_events_count,
            'proxy_events': proxy_events,
            'proxy_event_count': proxy_event_count,
            'doodle_count': doodle_count,
            'event_view': self.event_view,
        })
        return context


class PastEventListView(EventListView):

    template_name = 'cosinnus_event/event_list_detailed_past.html'
    event_view = 'past'
    filterset_class = EventFilter
    show_past_events = True
    
    def get_queryset(self):
        """ In the calendar we only show scheduled events """
        qs = self.get_base_queryset()
        qs = qs.filter(state=Event.STATE_SCHEDULED)
        qs = past_event_filter(qs).reverse()
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(PastEventListView, self).get_context_data(**kwargs)
        context['past_events'] = self.get_queryset()
        return context


class ConferenceEventListView(RequireWriteMixin, FilterGroupMixin, ListView):

    model = ConferenceEvent
    template_name = 'cosinnus_event/event_list_conference.html'
    
    def get_queryset(self):
        """ In the calendar we only show scheduled events """
        qs = super(ConferenceEventListView, self).get_queryset()
        qs = qs.filter(state=Event.STATE_SCHEDULED)
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(ConferenceEventListView, self).get_context_data(**kwargs)
        context['conference_events'] = context['object_list']
        context['object'] = self.group
        return context


class DoodleListView(EventListView):
    template_name = 'cosinnus_event/doodle_list.html'
    filterset_class = EventFilter

    def get_queryset(self):
        """In the doodle list we only show events with open votings"""
        qs = self.get_base_queryset()
        qs = qs.filter(state=Event.STATE_VOTING_OPEN)
        self.queryset = qs
        return qs


class ArchivedDoodlesListView(EventListView):

    template_name = 'cosinnus_event/doodle_list_detailed_archived.html'
    event_view = 'archived'
    filterset_class = EventFilter
    
    def get_queryset(self):
        """ In the calendar we only show scheduled events """
        qs = self.get_base_queryset()
        qs = qs.filter(state=Event.STATE_ARCHIVED_DOODLE).order_by('-created')
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(ArchivedDoodlesListView, self).get_context_data(**kwargs)
        context['archived_doodles'] = context.pop('future_events')
        return context


class DetailedEventListView(EventListView):
    template_name = 'cosinnus_event/event_list_detailed.html'
    filterset_class = EventFilter


class ConferencesListView(EventListView):
    """ Displays all conferences reflected into this group as events """
    template_name = 'cosinnus_event/event_list_detailed_conferences.html'
    event_view = 'conferences'
    filterset_class = EventFilter


class SuggestionInlineView(InlineFormSetFactory):
    extra = 1
    form_class = SuggestionForm
    model = Suggestion


class EntryFormMixin(RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin):
    form_class = EventForm
    model = Event
    message_success = _('Event "%(title)s" was edited successfully.')
    message_error = _('Event "%(title)s" could not be edited.')
    success_url_list = 'cosinnus:event:list'

    @dispatch_group_access()
    def dispatch(self, request, *args, **kwargs):
        if self.group.group_is_conference:
            messages.warning(request, _('Please use the conference management area to add new workshops!'))
            return redirect(group_aware_reverse('cosinnus:event:conference-event-list', kwargs={'group': self.group}))
        
        self.form_view = kwargs.get('form_view', None)
        if self.form_view != 'add':
            obj = self.get_object()
            if obj.state == Event.STATE_ARCHIVED_DOODLE and not self.form_view == 'delete':
                messages.warning(request, _('The page you requested is not available for this event at this time.'))
                return HttpResponseRedirect(obj.get_absolute_url())
            if self.form_view == 'delete':
                if obj.state == Event.STATE_VOTING_OPEN:
                    self.success_url_list = 'cosinnus:event:doodle-list'
                elif obj.state == Event.STATE_ARCHIVED_DOODLE:
                    self.success_url_list = 'cosinnus:event:doodle-list-archived'
        return super(EntryFormMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EntryFormMixin, self).get_context_data(**kwargs)
        tags = Event.objects.tags()
        context.update({
            'tags': tags,
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:event:event-detail'
        else:
            urlname = self.success_url_list
        return redirect_next_or(self.request, group_aware_reverse(urlname, kwargs=kwargs))

    def forms_valid(self, form, inlines):
        ret = super(EntryFormMixin, self).forms_valid(form, inlines)
        messages.success(self.request,
                         self.message_success % {'title': self.object.title})
        return ret

    def forms_invalid(self, form, inlines):
        ret = super(EntryFormMixin, self).forms_invalid(form, inlines)
        if self.object:
            messages.error(self.request,
                self.message_error % {'title': self.object.title})
        
        # we need to re-convert the string-date values in our suggestion fields so our hacky form template can read them
        datefield = forms.DateTimeField()
        for inline in inlines:
            data = inline.data
            data._mutable = True
            for key, val in list(data.items()):
                if key.startswith('suggestions-') and key.endswith('_date'):
                    try:
                        data[key] = datefield.to_python(val)
                        data[key] = datefield.to_python(val)
                    except ValidationError:
                        # cannot show errors on the suggestion fields themselves
                        if key.endswith('from_date'):
                            messages.error(self.request, _('One of the event suggestions times could not be understood!'))
        
        return ret


class DoodleFormMixin(EntryFormMixin):
    form_class = DoodleForm
    inlines = [SuggestionInlineView]
    template_name = "cosinnus_event/doodle_form.html"
    message_success = _('Unscheduled event "%(title)s" was edited successfully.')
    message_error = _('Unscheduled event "%(title)s" could not be edited.')

    def get_success_url(self):
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:event:doodle-vote'
        else:
            urlname = 'cosinnus:event:doodle-list'
        return group_aware_reverse(urlname, kwargs=kwargs)



class EntryAddView(EntryFormMixin, AttachableViewMixin, CreateWithInlinesView):
    message_success = _('Event "%(title)s" was added successfully.')
    message_error = _('Event "%(title)s" could not be added.')
    
    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        
        # events are created as scheduled.
        # doodle events would be created as STATE_VOTING_OPEN.
        form.instance.state = Event.STATE_SCHEDULED
        ret = super(EntryAddView, self).forms_valid(form, inlines)
        # creator follows their own event
        apply_likefollowstar_object(form.instance, self.request.user, follow=True)
        return ret


class DoodleAddView(DoodleFormMixin, AttachableViewMixin, CreateWithInlinesView):
    message_success = _('Unscheduled event "%(title)s" was added successfully.')
    message_error = _('Unscheduled event "%(title)s" could not be added.')

    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        form.instance.state = Event.STATE_VOTING_OPEN  # be explicit

        ret = super(DoodleAddView, self).forms_valid(form, inlines)
        # creator follows their own doodle
        apply_likefollowstar_object(form.instance, self.request.user, follow=True)
        
        # Check for non or a single suggestion and set it and inform the user
        num_suggs = self.object.suggestions.count()
        if num_suggs == 0:
            messages.info(self.request,
                _('You should define at least one date suggestion.'))
        return ret


class EntryEditView(EditViewWatchChangesMixin, EntryFormMixin, AttachableViewMixin, UpdateWithInlinesView):
    
    changed_attr_watchlist = ['title', 'note', 'from_date', 'to_date', 'media_tag.location','url',
                              'media_tag.location_lon', 'media_tag.location_lat', 'get_attached_objects_hash']


    def on_save_changed_attrs(self, obj, changed_attr_dict):
        if not obj.is_hidden_group_proxy:
            session_id = uuid1().int
            # send out a notification to all attendees for the change
            attendees_except_creator = [attendance.user.pk for attendance in obj.attendances.all() \
                                if (attendance.state in [EventAttendance.ATTENDANCE_GOING, EventAttendance.ATTENDANCE_MAYBE_GOING])\
                                    and not attendance.user.pk == obj.creator_id]
            cosinnus_notifications.attending_event_changed.send(sender=self, user=obj.creator, obj=obj, audience=get_user_model().objects.filter(id__in=attendees_except_creator), session_id=session_id)
            # send out a notification to all followers for the change
            followers_except_creator = [pk for pk in obj.get_followed_user_ids() if not pk in [obj.creator_id]]
            cosinnus_notifications.following_event_changed.send(sender=self, user=obj.creator, obj=obj, audience=get_user_model().objects.filter(id__in=followers_except_creator), session_id=session_id, end_session=True)


class DoodleEditView(EditViewWatchChangesMixin, DoodleFormMixin, AttachableViewMixin, UpdateWithInlinesView):
    
    changed_attr_watchlist = ['title', 'note', 'get_suggestions_hash', 'media_tag.location','url',
                          'media_tag.location_lon', 'media_tag.location_lat', 'get_attached_objects_hash']
    
    def on_save_changed_attrs(self, obj, changed_attr_dict):
        if not obj.is_hidden_group_proxy:
            # send out a notification to all followers for the change
            followers_except_creator = [pk for pk in obj.get_followed_user_ids() if not pk in [obj.creator_id]]
            cosinnus_notifications.following_doodle_changed.send(sender=self, user=obj.creator, obj=obj, audience=get_user_model().objects.filter(id__in=followers_except_creator))
    
    def get_context_data(self, *args, **kwargs):
        context = super(DoodleEditView, self).get_context_data(*args, **kwargs)
        context.update({
            'has_active_votes': self.object.suggestions.filter(votes__isnull=False).count() > 0,
        })
        return context
    
    def forms_valid(self, form, inlines):
        # Save the suggestions first so we can directly
        # access the amount of suggestions afterwards
        for formset in inlines:
            formset.save()

        suggestion = form.cleaned_data.get('suggestion')
        if not suggestion:
            num_suggs = form.instance.suggestions.count()
            if num_suggs == 0:
                suggestion = None
                messages.info(self.request,
                    _('You should define at least one date suggestion.'))
        # update_fields=None leads to saving the complete model, we
        # don't need to call obj.self here
        # INFO: set_suggestion saves the instance
        form.instance.set_suggestion(suggestion, update_fields=None)

        return super(DoodleEditView, self).forms_valid(form, inlines)


class EntryDeleteView(EntryFormMixin, DeleteView):
    message_success = _('Event "%(title)s" was deleted successfully.')
    message_error = _('Event "%(title)s" could not be deleted.')

    def get_success_url(self):
        urlname = getattr(self, 'success_url_list', 'cosinnus:event:list')
        return redirect_next_or(self.request, group_aware_reverse(urlname, kwargs={'group': self.group}))


class DoodleDeleteView(EntryFormMixin, DeleteView):
    message_success = _('Unscheduled event "%(title)s" was deleted successfully.')
    message_error = _('Unscheduled event "%(title)s" could not be deleted.')

    def get_success_url(self):
        urlname = getattr(self, 'success_url_list', 'cosinnus:event:doodle-list')
        return group_aware_reverse(urlname, kwargs={'group': self.group})


class EntryDetailView(ReflectedObjectRedirectNoticeMixin, ReflectedObjectSelectMixin, 
          RequireReadMixin, RecordLastVisitedMixin, FilterGroupMixin, DetailView):

    model = Event

    def get_context_data(self, **kwargs):
        context = super(EntryDetailView, self).get_context_data(**kwargs)
        event = context['object']
        user = self.request.user
        
        user_attendance = None if not user.is_authenticated else get_object_or_None(EventAttendance, user=user, event=event)
        all_attendants = EventAttendance.objects.filter(event=event)
        attendants_going = all_attendants.filter(state=EventAttendance.ATTENDANCE_GOING)
        attendants_maybe = all_attendants.filter(state=EventAttendance.ATTENDANCE_MAYBE_GOING)
        attendants_not_going = all_attendants.filter(state=EventAttendance.ATTENDANCE_NOT_GOING)

        context.update({
            'user_attendance': user_attendance,
            'attendants_going': attendants_going,
            'attendants_maybe': attendants_maybe,
            'attendants_not_going': attendants_not_going,
        })
        
        return context


class DoodleVoteView(RequireReadMixin, RecordLastVisitedMixin, FilterGroupMixin, SingleObjectMixin,
        FormSetView):

    message_success = _('Your votes were saved successfully.')
    message_error = _('Your votes could not be saved.')

    factory_kwargs = {'extra': 0}
    form_class = VoteForm
    model = Event
    template_name = 'cosinnus_event/doodle_vote.html'
    form_view = None # (set in urls.py), 'vote' or 'archived' or 'assign'
    
    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.state not in (Event.STATE_VOTING_OPEN, Event.STATE_ARCHIVED_DOODLE):
            messages.warning(request, _('The page you requested is not available for this event at this time.'))
            return HttpResponseRedirect(obj.get_absolute_url())
        return super(DoodleVoteView, self).get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        if self.get_object().state != Event.STATE_VOTING_OPEN:
            messages.error(request, _('This is event is already scheduled. You cannot vote for it any more.'))
            return HttpResponseRedirect(request.path)
        return super(DoodleVoteView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DoodleVoteView, self).get_context_data(**kwargs)
        
        # we group formsets, votes and suggestions by days (as in a day there might be more than one suggestion)
        # the absolute order inside the two lists when traversing the suggestions (iterated over days), 
        # is guaranteed to be sorted by date and time ascending, as is the user-grouped list of votes
        formset_forms_grouped = []
        vote_counts_grouped = []
        suggestions_list_grouped = []
        votes_user_grouped = defaultdict(list) # these are grouped by user, and sorted by suggestion, not day!
        for day, suggestions in sorted(list(self.suggestions_grouped.items()), key=lambda item: item[1][0].from_date):
            formset_forms_grouped_l = []
            vote_counts_grouped_l = []
            suggestions_list_grouped_l = []
            
            for suggestion in suggestions:
                suggestions_list_grouped_l.append(suggestion)
                # group the vote formsets in the same order we grouped the suggestions
                for form in context['formset'].forms:
                    if suggestion.pk == form.initial.get('suggestion', -1):
                        formset_forms_grouped_l.append(form)
                # create a grouped total count for all the votes
                # use sorted_votes here, it's cached
                # format: [no_votes, maybe_votes, yes_notes, is_most_overall_votes]
                counts = [0, 0, 0, False]
                for vote in suggestion.sorted_votes:
                    counts[vote.choice] += 1
                    votes_user_grouped[vote.voter.username].append(vote)
                vote_counts_grouped_l.append(counts)
            
            formset_forms_grouped.append(formset_forms_grouped_l)
            vote_counts_grouped.append(vote_counts_grouped_l)
            suggestions_list_grouped.append(suggestions_list_grouped_l)
        
        # determine and set the winning vote count of suggestions (if there are votes)
        try:
            max_vote_count = max([max([vote[2] for vote in votes]) for votes in vote_counts_grouped])
            for votes in vote_counts_grouped:
                for vote in votes:
                    if vote[2] == max_vote_count:
                        vote[3] = True
        except ValueError:
            pass
        
        context.update({
            'object': self.object,
            'suggestions': self.suggestions,
            'suggestions_grouped': suggestions_list_grouped,
            'formset_forms_grouped': formset_forms_grouped,
            'vote_counts_grouped': vote_counts_grouped,
            'votes_user_grouped': dict(votes_user_grouped),
        })
        return context

    def get_initial(self):
        self.object = self.get_object()
        self.suggestions = self.object.suggestions.order_by('from_date',
                                                            'to_date').all()
        
        self.suggestions_grouped = defaultdict(list)
        for suggestion in self.suggestions:
            self.suggestions_grouped[suggestion.from_date.date().isoformat()].append(suggestion)
                                                                    
        self.max_num = self.suggestions.count()
        self.initial = []
        for suggestion in self.suggestions:
            vote = None
            if self.request.user.is_authenticated:
                try:
                    vote = suggestion.votes.filter(voter=self.request.user).get()
                except Vote.DoesNotExist:
                    pass
            self.initial.append({
                'suggestion': suggestion.pk,
                'choice': vote.choice if vote else Vote.VOTE_NO,
            })
        return self.initial

    def get_success_url(self):
        kwargs = {'group': self.group, 'slug': self.object.slug}
        return group_aware_reverse('cosinnus:event:doodle-vote', kwargs=kwargs)

    def formset_valid(self, formset):
        for form in formset:
            cd = form.cleaned_data
            suggestion = int(cd.get('suggestion'))
            choice = int(cd.get('choice', 0))
            if suggestion:
                vote, _created = Vote.objects.get_or_create(suggestion_id=suggestion,
                                           voter=self.request.user)
                vote.choice = choice
                vote.save()
        
        ret = super(DoodleVoteView, self).formset_valid(formset)
        
        if not self.object.is_hidden_group_proxy:
            # send notification to followers
            followers_except_voter = [pk for pk in self.object.get_followed_user_ids() if not pk in [self.request.user.id]]
            cosinnus_notifications.following_doodle_voted.send(sender=self, user=self.request.user, obj=self.object, audience=get_user_model().objects.filter(id__in=followers_except_voter))
        
        messages.success(self.request, self.message_success )
        return ret
    
    def formset_invalid(self, formset):
        ret = super(DoodleVoteView, self).formset_invalid(formset)
        if self.object:
            messages.error(self.request, self.message_error)
        return ret


"""
class ArchivedDoodleView(DoodleVoteView):

    template_name = 'cosinnus_event/doodle_vote.html'
    form_view = None # (set in urls.py), 'vote' or 'archived' or 'assign'

archived_doodle_view = ArchivedDoodleView.as_view()
"""

class DoodleCompleteView(RequireWriteMixin, FilterGroupMixin, UpdateView):
    """ Completes a doodle event for a selected suggestion, setting the event to Scheduled. """
    form_class = EventNoFieldForm
    form_view = 'assign' 
    model = Event
    
    def get_object(self, queryset=None):
        obj = super(DoodleCompleteView, self).get_object(queryset)
        return obj
    
    def get(self, request, *args, **kwargs):
        # we don't accept GETs on this, just POSTs
        messages.error(request, _('The complete request can only be sent via POST!'))
        return HttpResponseRedirect(self.get_object().get_absolute_url())
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        event = self.object
        
        if self.object.state != Event.STATE_VOTING_OPEN:
            messages.error(request, _('This is event is already scheduled. You cannot vote for it any more.'))
            return HttpResponseRedirect(self.object.get_absolute_url())
        if 'suggestion_id' not in kwargs:
            messages.error(request, _('Event cannot be completed: No date was supplied.'))
            return HttpResponseRedirect(self.object.get_absolute_url())
        
        suggestion = get_object_or_404(Suggestion, pk=kwargs.get('suggestion_id'))
        old_doodle_pk = event.pk
        
        # give this a new temporary slug so the original one is free again
        event.slug += '-archive'
        unique_aware_slugify(event, 'title', 'slug', group=self.group, force_redo=True)
        event.created = now()
        event.save(update_fields=['slug', 'created'])
        
        # 'clone' media_tag
        new_media_tag = event.media_tag
        new_media_tag.pk = None 
        new_media_tag.save()
        
        event.pk = None # set pk to None to have this become a new event
        event.slug = None # set slug to None so we can re-unique slugify 
        event.media_tag = new_media_tag
        event.from_date = suggestion.from_date
        event.to_date = suggestion.to_date
        event.state = Event.STATE_SCHEDULED
        event.save(created_from_doodle=True)
        
        # re-retrieve old doodle, set it to archived 
        doodle = self.model.objects.get(pk=old_doodle_pk)
        doodle.state = Event.STATE_ARCHIVED_DOODLE
        doodle.save(update_fields=['state'])
        
        # link old doodle to new event. can't do this until now because we wouldn't have had the old pointer correctly
        event.original_doodle = doodle
        event.save(update_fields=['original_doodle'])
        
        messages.success(request, _('The event was created successfully at the specified date.'))
        return HttpResponseRedirect(self.object.get_absolute_url())


class BaseEventFeed(ICalFeed):
    """ A simple event calender feed. """
    
    PROTO_PRODUCT_ID = '-//%s//Event//Feed'
    
    product_id = None
    timezone = 'Europe/Berlin'
    base_title = _('Events') 
    title = None # set to base_title on init
    base_description = _('Upcoming events')
    description = None # set to base_description on init
    categories = None
    localtime = True # if given (?localtime=1), times will be converted to local server timezone time
    utc_offset = None # in hours, taken from ?utc_offset=<number> optional param
    filename = f"{_('Events')}.ics"

    def __init__(self, *args, **kwargs):
        self.title = self.base_title
        self.description = self.base_description
        return super(BaseEventFeed, self).__init__(*args, **kwargs)
    
    def __call__(self, request, *args, **kwargs):
        site = get_current_site(request)
        if not self.product_id:
            self.product_id = BaseEventFeed.PROTO_PRODUCT_ID % site.domain
        offset = request.GET.get('utc_offset', None)
        if offset and is_number(offset):
            self.utc_offset = int(offset)
        localtime = request.GET.get('localtime', None)
        if localtime is not None and is_number(localtime) and int(localtime) == 1:
            self.localtime = True
        if localtime is not None and is_number(localtime) and int(localtime) == 0:
            self.localtime = True
        response = super(BaseEventFeed, self).__call__(request, *args, **kwargs)
        response["Content-Disposition"] = 'attachment; filename="%s"' % self.get_filename(response)
        return response
    
    def get_feed(self, obj, request):
        self.request = request
        return super(BaseEventFeed, self).get_feed(obj, request)
    
    def items(self, request):
        # check if we should expand the group to sub
        include_sub_projects = self.request.GET.get('include_sub_projects', None) == '1'
        qs = Event.get_current(self.group, self.user, include_sub_projects=include_sub_projects)
        qs = qs.filter(state=Event.STATE_SCHEDULED, from_date__isnull=False, to_date__isnull=False).order_by('-from_date')
        return qs
    
    def item_title(self, item):
        return item.title

    def item_description(self, item):
        description = item.note
        # add website URL to description if set on event
        if item.url:
            description = description + '\n\n' + item.url if description else item.url 
        return description
    
    def _convert_datetime(self, item, datetime):
        # we're returning a DateTime here for a timed event and for a full-day event, we would return a Date
        if item.is_all_day:
            return localtime(datetime).date()
        if self.localtime:
            return localtime(datetime)
        if self.utc_offset:
            if self.utc_offset >= 0:
                return datetime + timedelta(hours=self.utc_offset)   
            else:
                return datetime - timedelta(hours=self.utc_offset*-1)
        return datetime

    def item_start_datetime(self, item):
        return self._convert_datetime(item, item.from_date)
    
    def item_end_datetime(self, item):
        if not item.is_all_day:
            return self._convert_datetime(item, item.to_date)
        return self._convert_datetime(item, item.to_date)  + timedelta(days=1)
    
    def item_link(self, item):
        return item.get_absolute_url()
    
    def item_location(self, item):
        mt = item.media_tag
        if mt and mt.location_lat and mt.location_lon and mt.location:
            return mt.location
        return None
    
    def item_geolocation(self, item):
        mt = item.media_tag
        if mt and mt.location_lat and mt.location_lon:
            return (mt.location_lat, mt.location_lon)
        return None

    def item_categories(self, item):
        from cosinnus.models.tagged import BaseTagObject

        mt = item.media_tag.tags.values_list('name', flat=True)
        mt = list(mt)

        ct = ensure_list_of_ints(item.media_tag.topics)
        choices_dict = dict(BaseTagObject.TOPIC_CHOICES)
        tl = [value for elem in ct for key, value in choices_dict.items() if elem==key]

        if mt or tl:
            return mt + tl
        return None

    def get_filename(self, response):
        return self.filename


class BaseGroupEventFeed(BaseEventFeed):
    """ A public iCal Feed that contains all publicly visible upcoming events (from the current portal only) """
    
    def __call__(self, request, *args, **kwargs):
        site = get_current_site(request)
        self.title = '%s - %s' %  (self.group.name, self.base_title)
        self.description = '%s - %s' % (self.base_description, self.group.name)
        if not self.product_id:
            self.product_id = UserTokenGroupEventFeed.PROTO_PRODUCT_ID % site.domain
        return super(BaseGroupEventFeed, self).__call__(request, *args, **kwargs)
    

class UserTokenGroupEventFeed(BaseGroupEventFeed):
    """ A group-based event feed. Uses a permanent user token for authentication
        (the token is only used for views displaying the user's event-feeds). """
    
    title = _('Events')
    description = _('Upcoming events')
    
    @require_user_token_access(settings.COSINNUS_EVENT_TOKEN_EVENT_FEED)
    def __call__(self, request, *args, **kwargs):
        return super(UserTokenGroupEventFeed, self).__call__(request, *args, **kwargs)


class UserTokenTeamEventFeed(BaseGroupEventFeed):
    """ A group-id-based event feed. Uses a permanent user token for authentication
        (the token is only used for views displaying the user's event-feeds). """

    title = _('Events')
    description = _('Upcoming events')

    @require_user_token_access(settings.COSINNUS_EVENT_TOKEN_EVENT_FEED, id_url_kwarg='team_id')
    def __call__(self, request, *args, **kwargs):
        return super(UserTokenTeamEventFeed, self).__call__(request, *args, **kwargs)


class PublicGroupEventFeed(BaseGroupEventFeed):
    """ A public iCal Feed that contains all publicly visible upcoming events (from the current portal only) """
    
    def __call__(self, request, *args, **kwargs):
        self.group = get_group_for_request(kwargs.get('group'), request)
        self.user = AnonymousUser()
        return super(PublicGroupEventFeed, self).__call__(request, *args, **kwargs)


class PublicTeamEventFeed(BaseGroupEventFeed):
    """ A public iCal Feed that contains all publicly visible upcoming events (from the current portal only).
        Refers to the id of a group directly. """

    def __call__(self, request, *args, **kwargs):
        team_id = kwargs.get('team_id')
        team = get_object_or_404(get_cosinnus_group_model(), id=team_id, portal_id=CosinnusPortal.get_current().id)
        self.group = ensure_group_type(team)
        self.user = AnonymousUser()
        return super(PublicTeamEventFeed, self).__call__(request, *args, **kwargs)


class GroupEventFeed(BaseEventFeed):
    """ This view is in place as first starting point for the Feeds, deciding whether it should
        show a token based or a public feed for this group. 
    
        DEPRECATED, in favor of TeamEventFeed. Left in for backwards compatibility for old ical imports."""
    
    def __call__(self, request, *args, **kwargs):
        if 'user' in request.GET and 'token' in request.GET:
            return user_token_group_event_feed(request, *args, **kwargs)
        else:
            return public_group_event_feed(request, *args, **kwargs)


class TeamEventFeed(BaseEventFeed):
    """ This view is in place as first starting point for the Feeds, deciding whether it should
        show a token based or a public feed for this group. Uses the group-id based views. """

    def __call__(self, request, *args, **kwargs):
        if 'user' in request.GET and 'token' in request.GET:
            return user_token_team_event_feed(request, *args, **kwargs)
        else:
            return public_team_event_feed(request, *args, **kwargs)


class GlobalFeed(BaseEventFeed):
    """ A public iCal Feed that contains all publicly visible upcoming events (from the current portal only) """

    def items(self, request):
        qs = Event.get_current_for_portal()
        qs = filter_tagged_object_queryset_for_user(qs, AnonymousUser())
        qs = qs.filter(state=Event.STATE_SCHEDULED, from_date__isnull=False, to_date__isnull=False).order_by(
            '-from_date')
        return qs


class BaseSingleEventFeed(BaseEventFeed):
    """ An iCal Feed that contains the event specified """
    model = Event

    def __call__(self, request, *args, **kwargs):
        # self.user is being set in either`PublicGroupSingleEventFeed`  
        # or the decorator `require_user_token_access`
        self.group = get_group_for_request(kwargs.get('group'), request)
        self.slug = kwargs.get('slug')
        return super(BaseSingleEventFeed, self).__call__(request, *args, **kwargs)

    def items(self, request):
        qs = self.model.objects.filter(group=self.group, state=Event.STATE_SCHEDULED)
        qs = filter_tagged_object_queryset_for_user(qs, self.user)
        return qs.filter(slug=self.slug)

    def get_filename(self, response):
        event = self.items(self.request).first()
        return event and f"{slugify(event.title)}.ics" or self.filename


class UserTokenSingleEventFeed(BaseSingleEventFeed):
    """ A group-based event feed. Uses a permanent user token for authentication
        (the token is only used for views displaying the user's event-feeds). """
    
    title = _('Event')
    description = _('Upcoming event')
    
    @require_user_token_access(settings.COSINNUS_EVENT_TOKEN_EVENT_FEED)
    def __call__(self, request, *args, **kwargs):
        return super(UserTokenSingleEventFeed, self).__call__(request, *args, **kwargs)


class TeamUserTokenSingleEventFeed(BaseSingleEventFeed):
    """ A group-id-based event feed. Uses a permanent user token for authentication
        (the token is only used for views displaying the user's event-feeds). """

    title = _('Event')
    description = _('Upcoming event')

    @require_user_token_access(settings.COSINNUS_EVENT_TOKEN_EVENT_FEED, id_url_kwarg='team_id')
    def __call__(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        return super(BaseSingleEventFeed, self).__call__(request, *args, **kwargs)


class PublicGroupSingleEventFeed(BaseSingleEventFeed):
    """ A public iCal Feed that contains all publicly visible upcoming events (from the current portal only) """
    
    def __call__(self, request, *args, **kwargs):
        self.group = get_group_for_request(kwargs.get('group'), request)
        self.user = AnonymousUser()
        return super(PublicGroupSingleEventFeed, self).__call__(request, *args, **kwargs)


class PublicTeamSingleEventFeed(BaseSingleEventFeed):
    """ A public iCal Feed that contains all publicly visible upcoming events (from the current portal only).
        Refers to the id of a group directly. """

    def __call__(self, request, *args, **kwargs):
        team_id = kwargs.get('team_id')
        team = get_object_or_404(get_cosinnus_group_model(), id=team_id, portal_id=CosinnusPortal.get_current().id)
        self.group = ensure_group_type(team)
        self.slug = kwargs.get('slug')
        self.user = AnonymousUser()
        return super(BaseSingleEventFeed, self).__call__(request, *args, **kwargs)


class SingleEventFeed(BaseEventFeed):
    """ This view is in place as first starting point for the single event Feeds, deciding whether it should
        show a token based or a public feed for this event. 
    
        DEPRECATED, in favor of TeamSingleEventFeed. Left in for backwards compatibility for old ical imports."""
    
    def __call__(self, request, *args, **kwargs):
        if 'user' in request.GET and 'token' in request.GET:
            return user_token_single_event_feed(request, *args, **kwargs)
        else:
            return public_group_single_event_feed(request, *args, **kwargs)


class TeamSingleEventFeed(BaseEventFeed):
    """ This view is in place as first starting point for the Feeds, deciding whether it should
        show a token based or a public feed for this group. Uses the group-id based views. """

    def __call__(self, request, *args, **kwargs):
        if 'user' in request.GET and 'token' in request.GET:
            return team_user_token_single_event_feed(request, *args, **kwargs)
        else:
            return public_team_single_event_feed(request, *args, **kwargs)


class PublicTeamSingleConferenceEventFeed(BaseSingleEventFeed):
    """ An iCal Feed that contains the conference event specified.
        Refers to the id of a group directly. """

    def __call__(self, request, *args, **kwargs):
        team_id = kwargs.get('team_id')
        team = get_object_or_404(get_cosinnus_group_model(), id=team_id, portal_id=CosinnusPortal.get_current().id)
        self.group = ensure_group_type(team)
        self.user = AnonymousUser()
        return super(PublicTeamSingleConferenceEventFeed).__call__(request, *args, **kwargs)


class SingleConferenceEventFeed(SingleEventFeed):
    """ An iCal Feed that contains the conference event specified.
    
        DEPRECATED, in favor of TeamSingleConferenceEventFeed. Left in for backwards compatibility for old ical imports. """
    model = ConferenceEvent

    def item_location(self, item):
        return item.room.title

    def item_geolocation(self, item):
        return None


class TeamSingleConferenceEventFeed(TeamSingleEventFeed):
    """ An iCal Feed that contains the conference event specified.
        Refers to the id of a group directly. """

    model = ConferenceEvent

    def item_location(self, item):
        return item.room.title

    def item_geolocation(self, item):
        return None


class CommentCreateView(RequireWriteMixin, FilterGroupMixin, AjaxFormsCommentCreateViewMixin,
        CreateView):

    form_class = CommentForm
    group_field = 'event__group'
    model = Comment
    template_name = 'cosinnus_event/event_detail.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.event = self.event
        messages.success(self.request, self.message_success)
        ret = super(CommentCreateView, self).form_valid(form)
        self.event.update_last_action(now(), self.request.user, save=True)
        return ret

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the event as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'event': self.event,
            'object': self.event, 
        })
        return context

    def get(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, group=self.group, slug=self.kwargs.get('event_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, group=self.group, slug=self.kwargs.get('event_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.event.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, AjaxFormsDeleteViewMixin, DeleteView):

    group_field = 'event__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'event': self.object.event})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.event.group.get_absolute_url())
        return super(CommentDeleteView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        messages.success(self.request, self.message_success)
        return self.referer


class CommentDetailView(SingleObjectMixin, RedirectView):

    permanent = False
    model = Comment

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        return HttpResponseRedirect(obj.get_absolute_url())


class CommentUpdateView(RequireWriteMixin, FilterGroupMixin, UpdateView):

    form_class = CommentForm
    group_field = 'event__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'event': self.object.event})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.event.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer


@csrf_protect
def assign_attendance_view(request, group, slug):
    """ Assign attendance for an event. 
        POST param: ``target_state``: Numerical for EventAttendance::ATTENDANCE_STATES.
            Pass '-1' to remove the attending object, i.e. the 'no choice selected' state.  """
    
    if not request.is_ajax():
        return HttpResponseBadRequest("This can only be called via Ajax.")
    user = request.user
    if not user.is_authenticated:
        return HttpResponseBadRequest("This can only be called for logged in users.")
    
    target_state = request.POST.get('target_state', None)
    try:
        target_state = int(target_state)
    except:
        pass
    if target_state != -1 and target_state not in list(dict(EventAttendance.ATTENDANCE_STATES).keys()):
        target_state = None
    
    if target_state is None:
        return HttpResponseBadRequest("Missing or malformed POST parameter: 'target_state'")
    
    group = get_group_for_request(group, request)
    if not group:
        logger.error('No group found when trying to assign attendance to an event!', extra={'group_slug': group, 
            'request': request, 'path': request.path})
        return JsonResponse({'error': 'groupnotfound'})
    
    event = get_object_or_None(Event, slug=slug, group=group)
    if not event:
        logger.error('No event found when trying to assign attendance to an event!', extra={'event_slug': slug, 
            'request': request, 'path': request.path})
        return JsonResponse({'error': 'eventnotfound'})
    
    event = get_object_or_None(Event, slug=slug, group=group)
    if not event.state == Event.STATE_SCHEDULED:
        return JsonResponse({'error': 'eventnotactive'})
    
    if not check_object_read_access(event, user):
        logger.warn('Permission error while assigning attendance for an event!', 
             extra={'user': user, 'request': request, 'path': request.path, 'group_slug': group, 'event_slug': slug})
        return JsonResponse({'error': 'denied'})
    
    result_state = None
    try:
        attendance = get_object_or_None(EventAttendance, event=event, user=user)
        if (attendance is None and target_state == -1) or (attendance is not None and target_state == attendance.state):
            # no action required
            result_state = target_state
        elif attendance is not None and target_state == -1:
            attendance.delete()
            result_state = -1
        elif attendance is not None:
            attendance.state = target_state
            attendance.save(update_fields=['state', 'date'])
            result_state = attendance.state
        else:
            attendance = EventAttendance.objects.create(event=event, user=user, state=target_state)
            result_state = attendance.state
        # update search index for the event to reindex it
        event.update_index()
            
    except Exception as e:
        logger.error('Exception while assigning attendance for an event!', 
             extra={'user': user, 'request': request, 'path': request.path, 'group_slug': group, 'event_slug': slug, 'exception': str(e)})
    
    if result_state is not None:
        return JsonResponse({'status': 'ok', 'result_state': result_state})
    
    return JsonResponse({'error': 'statecouldnotbechanged', 'result_state': -1 if attendance is None else attendance.state})


class EventDeleteElementView(DeleteElementView):
    model = Event


class ConferenceEventFormMixin(RequireWriteMixin, FilterGroupMixin, FilterConferenceRoomMixin,
                     GroupFormKwargsMixin, UserFormKwargsMixin):
    
    model = ConferenceEvent
    template_name = 'cosinnus_event/conference_event_form.html'
    message_success = _('Event "%(title)s" was edited successfully.')
    message_error = _('Event "%(title)s" could not be edited.')
    form_view = None
    
    CONFERENCE_EVENT_FORMS_BY_ROOM_TYPE = {
        CosinnusConferenceRoom.TYPE_LOBBY: ConferenceEventLobbyForm,
        CosinnusConferenceRoom.TYPE_STAGE: ConferenceEventStageForm,
        CosinnusConferenceRoom.TYPE_WORKSHOPS: ConferenceEventWorkshopForm,
        CosinnusConferenceRoom.TYPE_DISCUSSIONS: ConferenceEventDiscussionForm,
        CosinnusConferenceRoom.TYPE_COFFEE_TABLES: ConferenceEventCoffeeTableForm,
    }

    @dispatch_group_access()
    def dispatch(self, request, *args, **kwargs):
        try:
            ret = super(ConferenceEventFormMixin, self).dispatch(request, *args, **kwargs)
        except ImproperlyConfigured as e:
            logger.error(e)
            return redirect_to_403(self.request, self)
        return ret
    
    def get_form_class(self):
        klass = self.CONFERENCE_EVENT_FORMS_BY_ROOM_TYPE.get(self.room.type, None)
        if klass is None:
            raise ImproperlyConfigured('ConferenceEvent Form type not found for conference room type "%s"' % self.room.type)
        return klass
    
    """
    Disabled until we can figure out how to keep the kwargs getting passed to the MultiModelForm first
    def get_form_kwargs(self):
        form_kwargs = super(ConferenceEventFormMixin, self).get_form_kwargs()
        form_kwargs['room'] = self.room
        return form_kwargs
    """
    
    def get_context_data(self, **kwargs):
        context = super(ConferenceEventFormMixin, self).get_context_data(**kwargs)
        tags = ConferenceEvent.objects.tags()
        context.update({
            'tags': tags,
            'form_view': self.form_view,
            'room': self.room,
            'event_type_verbose': dict(ConferenceEvent.TYPE_CHOICES)[ConferenceEvent.CONFERENCE_EVENT_TYPE_BY_ROOM_TYPE.get(self.room.type)],
        })
        return context

    def get_success_url(self):
        if 'create_another' in self.request.POST:
            url = group_aware_reverse('cosinnus:event:conference-event-add',
                                      kwargs={'room_slug': self.room.slug,
                                              'group': self.group})
            if self.object.to_date:
                last_date = self.object.to_date
                one_hour_later = last_date + timedelta(hours=1)
                start_date = last_date.strftime("%Y-%m-%d")
                to_date = one_hour_later.strftime("%Y-%m-%d")
                start_time = last_date.strftime("%H:%M")
                end_time = one_hour_later.strftime("%H:%M")
                if start_date:
                    url = '{}?start={}&end={}&starttime={}&endtime={}'.format(
                        url,
                        start_date,
                        to_date,
                        start_time,
                        end_time
                    )
        else:
            # redirect to room, except in compact mode where we redirect to the conference event list
            if settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
                url = group_aware_reverse('cosinnus:event:conference-event-list', kwargs={'group': self.group})
            else:
                url = self.room.get_absolute_url()
        return redirect_next_or(self.request, url)

    def forms_valid(self, form, inlines):
        # assign room to ConferenceEvent
        form.instance.room = self.room
        ret = super(ConferenceEventFormMixin, self).forms_valid(form, inlines)
        messages.success(self.request,
            self.message_success % {'title': self.object.title})
        return ret


class ConferenceEventAddView(ConferenceEventFormMixin, AttachableViewMixin, CreateWithInlinesView):
    message_success = _('Event "%(title)s" was added successfully.')
    message_error = _('Event "%(title)s" could not be added.')
    form_view = 'add'
    
    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        
        # events are created as scheduled.
        form.instance.state = Event.STATE_SCHEDULED
        ret = super(ConferenceEventAddView, self).forms_valid(form, inlines)
        return ret


class ConferenceEventEditView(ConferenceEventFormMixin, AttachableViewMixin, UpdateWithInlinesView):
    form_view = 'edit'


class ConferenceEventDeleteView(ConferenceEventFormMixin, DeleteView):
    message_success = _('Event "%(title)s" was deleted successfully.')
    message_error = _('Event "%(title)s" could not be deleted.')


def event_api_update(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        if check_object_write_access(event, user):
            start = dateutil.parser.parse(request.POST.get('start'))
            end = dateutil.parser.parse(request.POST.get('end'))
            event.from_date = start
            event.to_date = end
            event.save()
            return JsonResponse({'status': 'success'})
        else:
            raise PermissionDenied()
    return HttpResponseNotAllowed(['post'])


index_view = EventIndexView.as_view()
list_view = EventListView.as_view()
past_events_list_view = PastEventListView.as_view()
conference_event_list_view = ConferenceEventListView.as_view()
doodle_list_view = DoodleListView.as_view()
archived_doodles_list_view = ArchivedDoodlesListView.as_view()
detailed_list_view = DetailedEventListView.as_view()
conference_list_view = ConferencesListView.as_view()
entry_add_view = EntryAddView.as_view()
doodle_add_view = DoodleAddView.as_view()
entry_edit_view = EntryEditView.as_view()
doodle_edit_view = DoodleEditView.as_view()
entry_delete_view = EntryDeleteView.as_view()
doodle_delete_view = DoodleDeleteView.as_view()
entry_detail_view = EntryDetailView.as_view()
doodle_vote_view = DoodleVoteView.as_view()
doodle_complete_view = DoodleCompleteView.as_view()
user_token_group_event_feed = UserTokenGroupEventFeed()
user_token_team_event_feed = UserTokenTeamEventFeed()
public_group_event_feed = PublicGroupEventFeed()
public_team_event_feed = PublicTeamEventFeed()
user_token_single_event_feed = UserTokenSingleEventFeed()
team_user_token_single_event_feed = TeamUserTokenSingleEventFeed()
public_group_single_event_feed = PublicGroupSingleEventFeed()
public_team_single_event_feed = PublicTeamSingleEventFeed()
event_ical_feed = GroupEventFeed()
team_event_ical_feed = TeamEventFeed()
event_ical_feed_global = GlobalFeed()
event_ical_feed_single = SingleEventFeed()
team_event_ical_feed_single = TeamSingleEventFeed()
conference_event_ical_feed_single = SingleConferenceEventFeed()
team_conference_event_ical_feed_single = TeamSingleConferenceEventFeed()
comment_create = CommentCreateView.as_view()
comment_delete = CommentDeleteView.as_view()
comment_detail = CommentDetailView.as_view()
comment_update = CommentUpdateView.as_view()
delete_element_view = EventDeleteElementView.as_view()
conference_event_add_view = ConferenceEventAddView.as_view()
conference_event_edit_view = ConferenceEventEditView.as_view()
conference_event_delete_view = ConferenceEventDeleteView.as_view()
