# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from _collections import defaultdict
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models.aggregates import Sum
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import UpdateView

from cosinnus.conf import settings
from cosinnus.models.conference import (
    CosinnusConferencePremiumBlock,
    CosinnusConferencePremiumCapacityInfo,
    CosinnusConferenceRoom,
    CosinnusConferenceSettings,
)
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusConference
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.user import filter_active_users, filter_portal_users
from cosinnus.views.mixins.group import RequirePortalManagerMixin
from cosinnus_conference.forms import ConferencePremiumBlockForm


class ConferenceAdministrationView(RedirectView):
    permanent = False
    url = reverse_lazy('cosinnus:conference-administration-overview')


conference_administration = ConferenceAdministrationView.as_view()


class ConferenceOverviewView(RequirePortalManagerMixin, TemplateView):
    """A deep-down report list view of all conferences, their rooms, events,
    and for all of those, their `CosinnusConferenceSettings` if they have one assigned.

    Kwargs:
        - only_nonstandard: if True, only objects with a set `CosinnusConferenceSettings`
            will be listed
    """

    template_name = 'cosinnus/administration/conference_overview.html'
    only_nonstandard = False
    only_premium = False
    past = False

    def dispatch(self, request, *args, **kwargs):
        self.only_nonstandard = kwargs.pop('only_nonstandard', self.only_nonstandard)
        self.only_premium = kwargs.pop('only_premium', self.only_premium)
        self.past = request.GET.get('past', self.past)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'toggle_permanent_premium' in request.POST:
            conference_id = request.POST.get('toggle_permanent_premium')
            if conference_id:
                conference = CosinnusConference.objects.filter(id=conference_id).first()
                conference.is_premium_permanently = not conference.is_premium_permanently
                conference.save()
                if conference.is_premium_permanently:
                    messages.add_message(request, messages.SUCCESS, _('Successfully made conference permanent premium'))
                else:
                    messages.add_message(
                        request, messages.SUCCESS, _('Successfully removed permanent premium from conference')
                    )

        return self.render_to_response(self.get_context_data(*args, **kwargs))

    def get_context_data(self, *args, **kwargs):
        """Gather all conferences, and their rooms and those rooms' events and for each of those,
        their conference setting object, if one exists.
        If self.only_nonstandard view option is set, we only show items if they have a conference setting item,
        otherwise we list all of them.
        If self.only_premoum view option is set, we only show items from conferences that have at least one
        premium block.
        """
        context = super(ConferenceOverviewView, self).get_context_data(*args, **kwargs)

        # split conferences by soonest running first, then list all finished ones
        conferences = (
            CosinnusConference.objects.all_in_portal().order_by('from_date').prefetch_related('rooms', 'rooms__events')
        )
        filtered_conferences = None
        if self.past:
            filtered_conferences = conferences.exclude(to_date__gte=now())
        else:
            filtered_conferences = conferences.filter(to_date__gte=now())

        if self.only_premium:
            filtered_conferences = filtered_conferences.filter_is_any_premium()

        # make a cached list for conference settings
        all_settings = CosinnusConferenceSettings.objects.all()
        conference_settings_dict = defaultdict(dict)
        for sett in all_settings:
            conference_settings_dict[sett.content_type_id][sett.object_id] = sett
        conference_ct_id = ContentType.objects.get_for_model(CosinnusConference).id
        room_ct_id = ContentType.objects.get_for_model(CosinnusConferenceRoom).id
        from cosinnus_event.models import ConferenceEvent  # noqa

        event_ct_id = ContentType.objects.get_for_model(ConferenceEvent).id

        conference_report_list = []
        shown_conferences = []
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
                shown_conferences.append(conference)

        portal = CosinnusPortal.get_current()
        context.update(
            {
                'portal': portal,
                'portal_setting': CosinnusConferenceSettings.get_for_object(portal),
                'conference_report_list': conference_report_list,
                'only_nonstandard': self.only_nonstandard,
                'only_premium': self.only_premium,
                'conferences': shown_conferences,
                'past': self.past,
            }
        )
        # additional data for the calendar view on the premium overview page
        # in both current/past views, the date border is actually 4 weeks beyond today for convenience
        portal_capacity_blocks = CosinnusConferencePremiumCapacityInfo.objects.filter(portal=portal)
        if self.past:
            now_date = (now() + timedelta(weeks=4)).date()
            portal_capacity_blocks = portal_capacity_blocks.filter(from_date__lte=now() + timedelta(weeks=4))
        else:
            now_date = (now() - timedelta(weeks=4)).date()
            portal_capacity_blocks = portal_capacity_blocks.filter(to_date__gte=now() - timedelta(weeks=4))
        # create a daily block with
        generated_capacity_blocks = []
        for capacity_block in portal_capacity_blocks:
            cur_date = capacity_block.from_date
            # loop over each day of each portal block and get the total capacity of all premium blocks for that day
            while cur_date <= capacity_block.to_date:
                if not (self.past and cur_date >= now_date) and not (not self.past and cur_date <= now_date):
                    premium_capacity = (
                        CosinnusConferencePremiumBlock.objects.filter(conference__portal=portal)
                        .filter(from_date__lte=cur_date, to_date__gte=cur_date)
                        .aggregate(Sum('participants'))
                        .get('participants__sum', None)
                    )
                    generated_capacity_blocks.append(
                        {
                            'date': cur_date,
                            'total': capacity_block.max_participants,
                            'premium': premium_capacity or 0,
                        }
                    )
                # step forward one day
                cur_date = cur_date + timedelta(days=1)

        # paid_payments_month.aggregate(Sum('amount')).get('amount__sum', None)
        conference_premium_blocks = []
        for conference in filtered_conferences:
            filtered_conf_blocks = conference.conference_premium_blocks.all()
            if self.past:
                filtered_conf_blocks = filtered_conf_blocks.filter(to_date__lte=now_date)
            else:
                filtered_conf_blocks = filtered_conf_blocks.filter(to_date__gte=now_date)
            conference_premium_blocks.extend(list(filtered_conf_blocks))
        context.update(
            {
                'portal_capacity_blocks': portal_capacity_blocks,
                'generated_capacity_blocks': generated_capacity_blocks,
                'conference_premium_blocks': conference_premium_blocks,
            }
        )
        # Temporary change, delete when the conference premium block forms are in!
        context.update(
            {
                'all_superusers': filter_active_users(
                    filter_portal_users(get_user_model().objects.filter(is_superuser=True))
                )
            }
        )
        return context


class ConferenceAddPremiumBlockView(RequirePortalManagerMixin, FormView):
    template_name = 'cosinnus/administration/conference_premium_block_form.html'
    form_class = ConferencePremiumBlockForm

    def get_conference(self):
        slug = self.kwargs.get('slug')
        cosinnus_group = get_cosinnus_group_model()
        return cosinnus_group.objects.get(slug=slug)

    def form_valid(self, form):
        form.instance.conference = self.get_conference()
        form.instance.save()
        messages.add_message(self.request, messages.SUCCESS, _('Successfully added premium block'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cosinnus:conference-administration-overview')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conference = self.get_conference()
        context.update({'conference': conference, 'title': _('Add Premium Block to "{}"').format(conference.name)})
        return context


class ConferenceEditPremiumBlockView(SuccessMessageMixin, RequirePortalManagerMixin, UpdateView):
    template_name = 'cosinnus/administration/conference_premium_block_form.html'
    model = CosinnusConferencePremiumBlock
    form_class = ConferencePremiumBlockForm
    success_message = _('Successfully updated premium block.')
    pk_url_kwarg = 'block_id'

    def get_conference(self):
        return self.object.conference

    def get_success_url(self):
        return reverse_lazy('cosinnus:conference-administration-overview')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conference = self.get_conference()
        context.update(
            {'conference': conference, 'title': _('Edit Premium Block in conference "{}"').format(conference.name)}
        )
        return context

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            self.get_object().delete()
            messages.add_message(request, messages.SUCCESS, _('Successfully deleted premium block'))
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)


conference_overview = ConferenceOverviewView.as_view()
conference_add_premium_block = ConferenceAddPremiumBlockView.as_view()
conference_edit_premium_block = ConferenceEditPremiumBlockView.as_view()
