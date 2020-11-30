# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.utils.user import filter_active_users
from cosinnus.models.group import CosinnusPortal
from django.contrib.auth import get_user_model
from django.views.generic.edit import FormView
from cosinnus.forms.statistics import SimpleStatisticsForm
from cosinnus.utils.permissions import check_user_superuser
from django.core.exceptions import PermissionDenied
from datetime import datetime
from cosinnus.models.bbb_room import BBBRoomVisitStatistics
from cosinnus.utils.http import make_csv_response
from django.http.response import HttpResponseForbidden
from django.utils import timezone


class SimpleStatisticsView(FormView):
    
    DATE_FORMAT = '%Y-%m-%d-%H:%M'
    
    form_class = SimpleStatisticsForm
    template_name = 'cosinnus/statistics/simple.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
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
        active_projects = CosinnusProject.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__lte=to_date).count()
        active_groups = CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__lte=to_date).count()
        
        statistics = {
            '1. New Registered Users': created_users,
            '2. Active Users': active_users,
            '3. New Created Projects': created_projects,
            '4. Active Projects': active_projects,
            '5. New Created Groups': created_groups,
            '6. Active Groups': active_groups,
        }
        try:
            from cosinnus_event.models import Event
            created_event_count = Event.objects.filter(group__portal=CosinnusPortal.get_current(), created__gte=from_date, created__lte=to_date).count()
            statistics.update({
                '7. Created Events': created_event_count,      
            })
        except:
            pass
        
        try:
            from cosinnus_note.models import Note
            created_note_count = Note.objects.filter(group__portal=CosinnusPortal.get_current(), created__gte=from_date, created__lte=to_date).count()
            statistics.update({
                '8. Created News': created_note_count,      
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
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    rows = []
    headers = [
        'datetime',
        'conference_name',
        'room_name',
        'user_id',
        'user_mtag_ids',
        'user_mtag_slugs',
        'group_mtag_ids',
        'group_mtag_slugs',
    ]
    
    for visit in BBBRoomVisitStatistics.objects.all().order_by('visit_datetime'):
        rows.append([
            timezone.localtime(visit.visit_datetime).strftime('%Y-%m-%d %H:%M:%S'), # 'datetime',
            visit.group and visit.group.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_NAME, ''), #'conference_name',
            visit.bbb_room and visit.bbb_room.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_ROOM_NAME, ''), #'room_name',
            visit.user and visit.user.id or '<no-user>', #'user_id',
            ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_USER_MANAGED_TAG_IDS, [])]), #'user_mtag_ids',
            ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS, [])]), #'user_mtag_slugs',
            ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_MANAGED_TAG_IDS, [])]), #'group_mtag_ids',
            ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS, [])]), #'group_mtag_slugs',
        ])
        
    return make_csv_response(rows, headers, 'bbb-room-visits')




