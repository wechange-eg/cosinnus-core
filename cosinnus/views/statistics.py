# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.views.generic.edit import FormView

from cosinnus.forms.statistics import SimpleStatisticsForm
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject, \
    CosinnusConference
from cosinnus.utils.user import filter_active_users
from cosinnus.views.mixins.group import RequirePortalManagerMixin


class SimpleStatisticsView(RequirePortalManagerMixin, FormView):
    
    DATE_FORMAT = '%Y-%m-%d-%H:%M'
    
    form_class = SimpleStatisticsForm
    template_name = 'cosinnus/statistics/simple.html'
    
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
