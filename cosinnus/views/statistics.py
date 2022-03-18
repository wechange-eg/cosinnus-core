# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http.response import HttpResponseForbidden
from django.utils import timezone
from django.views.generic.edit import FormView

from cosinnus.forms.statistics import SimpleStatisticsForm
from cosinnus.models.bbb_room import BBBRoomVisitStatistics
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject, \
    CosinnusConference
from cosinnus.utils.http import make_csv_response
from cosinnus.utils.permissions import check_user_superuser, check_user_portal_manager
from cosinnus.utils.user import filter_active_users


class SimpleStatisticsView(FormView):
    
    DATE_FORMAT = '%Y-%m-%d-%H:%M'
    
    form_class = SimpleStatisticsForm
    template_name = 'cosinnus/statistics/simple.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user) and not check_user_portal_manager(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super(SimpleStatisticsView, self).dispatch(request, *args, **kwargs)
    
    def get_initial(self, *args, **kwargs):
        initial = super(SimpleStatisticsView, self).get_initial(*args, **kwargs)
        if self.request.method == 'GET' and 'from' in self.request.GET and 'to' in self.request.GET:
            initial.update({
                'from_date': datetime.strptime(self.request.GET.get('from'), SimpleStatisticsView.DATE_FORMAT),
                'to_date': datetime.strptime(self.request.GET.get('to'), SimpleStatisticsView.DATE_FORMAT),
            })
        return initial
    
    def get_context_data(self, *args, **kwargs):
        context = super(SimpleStatisticsView, self).get_context_data(*args, **kwargs)
        if self.request.method == 'GET' and 'from' in self.request.GET and 'to' in self.request.GET:
            from_date = context['form'].initial['from_date']
            to_date =  context['form'].initial['to_date']
            context.update({
                'statistics': self.get_statistics(from_date, to_date)
            })
        return context
    
    
    def get_statistics(self, from_date, to_date):
        """ Actual collection of data """
        created_users = filter_active_users(get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members))\
            .filter(date_joined__gte=from_date, date_joined__lte=to_date).count()
        active_users = filter_active_users(get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members))\
            .filter(date_joined__lte=to_date).count()
        created_projects = CosinnusProject.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__gte=from_date, created__lte=to_date).count()
        created_groups = CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True,  created__gte=from_date, created__lte=to_date).count()
        created_conferences = CosinnusConference.objects.filter(portal=CosinnusPortal.get_current(), is_active=True,  created__gte=from_date, created__lte=to_date).count()
        active_projects = CosinnusProject.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__lte=to_date).count()
        active_groups = CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__lte=to_date).count()
        active_conferences = CosinnusConference.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__lte=to_date).count()
        running_conferences = CosinnusConference.objects.filter(portal=CosinnusPortal.get_current(), is_active=True)\
            .filter(
                (Q(from_date__gte=from_date) & Q(to_date__lte=to_date)) | \
                (Q(to_date__gte=from_date) & Q(to_date__lte=to_date)) | \
                (Q(from_date__lte=from_date) & Q(to_date__gte=to_date))
            ).count()
        
        
        statistics = {
            '01. New Registered Users': created_users,
            '02. Active Users': active_users,
            '03. New Created Projects': created_projects,
            '04. Active Projects': active_projects,
            '05. New Created Groups': created_groups,
            '06. Active Groups': active_groups,
            '07. New Created Conferences': created_conferences,
            '08. Active Conferences': active_conferences,
            '09. Running (scheduled) Conferences': running_conferences,
        }
        try:
            from cosinnus_event.models import Event
            created_event_count = Event.objects.filter(group__portal=CosinnusPortal.get_current(), created__gte=from_date, created__lte=to_date).count()
            statistics.update({
                '10. Created Events': created_event_count,      
            })
        except:
            pass
        
        try:
            from cosinnus_note.models import Note
            created_note_count = Note.objects.filter(group__portal=CosinnusPortal.get_current(), created__gte=from_date, created__lte=to_date).count()
            statistics.update({
                '11. Created News': created_note_count,      
            })
        except:
            pass
        statistics = sorted(statistics.items())
        return statistics
    
    def form_valid(self, form):
        self.form = form
        return super(SimpleStatisticsView, self).form_valid(form)
    
    def get_success_url(self):
        params = {
            'from': self.form.cleaned_data['from_date'].strftime(SimpleStatisticsView.DATE_FORMAT),
            'to': self.form.cleaned_data['to_date'].strftime(SimpleStatisticsView.DATE_FORMAT),
        }
        return '.?from=%(from)s&to=%(to)s' % params


simple_statistics = SimpleStatisticsView.as_view()


def bbb_room_visit_statistics_download(request):
    """
        Will return a CSV containing infos about all BBB Room visits
    """
    if request and not check_user_superuser(request.user):
        return HttpResponseForbidden('Not authenticated')
    
    rows = []
    headers = [
        'datetime',
        'conference_name',
        'conference_mtag_slugs',
        'conference_creator_email_language',
        'room_name',
        'visitor_id',
        'visitor_mtag_slugs',
        'visitor_email_language',
        'visitor_location',
        'visitor_location_lat',
        'visitor_location_lon',
    ]
    #'user_mtag_ids',
    #'conference_mtag_ids',
    
    # cache for group_id (int) -> user
    group_admin_cache = {}
    for visit in BBBRoomVisitStatistics.objects.all().order_by('visit_datetime').\
            prefetch_related('user', 'user__cosinnus_profile', 'user__cosinnus_profile__media_tag',
                             'group', 'bbb_room'):
        visitor = visit.user or None
        visitor_mt = visitor and visitor.cosinnus_profile and visitor.cosinnus_profile.media_tag or None
        # cache the group-admins
        visited_group_admin = group_admin_cache.get(visit.group_id, None)
        if visited_group_admin is None:
            visited_group_admins = visit.group and visit.group.actual_admins or []
            # only reporting data on the first admin for simplicity
            visited_group_admin = len(visited_group_admins) > 0 and visited_group_admins[0] or None
            group_admin_cache[visit.group_id] = visited_group_admin
            
        rows.append([
            timezone.localtime(visit.visit_datetime).strftime('%Y-%m-%d %H:%M:%S'), # 'datetime',
            visit.group and visit.group.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_NAME, ''), #'conference_name',
            ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS, [])]), #'conference_mtag_slugs',
            visited_group_admin.cosinnus_profile.language if visited_group_admin else '<no-user>', # conference_creator_email_language
            visit.bbb_room and visit.bbb_room.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_ROOM_NAME, ''), #'room_name',
            visitor.id if visitor else '<no-user>', #'visitor_id',
            ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS, [])]), #'visitor_mtag_slugs',
            visitor.cosinnus_profile.language if visitor else '<no-user>', # visitor_email_language
            visitor_mt and visitor_mt.location if visitor_mt else '', # visitor_location
            visitor_mt.location_lat if visitor_mt and visitor_mt.location else '', # visitor_location_lat
            visitor_mt.location_lon if visitor_mt and visitor_mt.location else '', # visitor_location_lon
        ])
        #','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_USER_MANAGED_TAG_IDS, [])]), #'user_mtag_ids',
        #','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_MANAGED_TAG_IDS, [])]), #'group_mtag_ids',
        
    return make_csv_response(rows, headers, 'bbb-room-visits')




