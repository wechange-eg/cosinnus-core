# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http.response import JsonResponse
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.utils.user import filter_active_users
from cosinnus.models.group import CosinnusPortal
from django.contrib.auth import get_user_model
from django.views.generic.edit import FormView
from cosinnus.forms.statistics import SimpleStatisticsForm
from cosinnus.utils.permissions import check_user_superuser
from django.core.exceptions import PermissionDenied
from datetime import datetime


def general(request):
    """ Returns a JSON dict of common statistics for this portal """
    
    all_users_qs = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members)
    data = {
        'groups': CosinnusSociety.objects.all_in_portal().count(),
        'projects': CosinnusProject.objects.all_in_portal().count(),
        'users_registered': all_users_qs.count(),
        'users_active': filter_active_users(all_users_qs).count(),
    }
    try:
        from cosinnus_event.models import Event
        upcoming_event_count = Event.get_current_for_portal().count()
        data.update({
            'events_upcoming': upcoming_event_count,      
        })
    except:
        pass
    
    try:
        from cosinnus_note.models import Note
        note_count = Note.get_current_for_portal().count()
        data.update({
            'notes': note_count,      
        })
    except:
        pass
    
    return JsonResponse(data)


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
        registered_users = filter_active_users(get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members))\
            .filter(date_joined__gte=from_date, date_joined__lte=to_date).count()
        # note: pre-existing groups count as well!
        active_projects = CosinnusProject.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__lte=to_date).count()
        active_groups = CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True, created__lte=to_date).count()
        
        statistics = {
            '1. Registered Users': registered_users,
            '2. Active Projects': active_projects,
            '3. Active Groups': active_groups,
        }
        try:
            from cosinnus_event.models import Event
            created_event_count = Event.objects.filter(group__portal=CosinnusPortal.get_current(), created__gte=from_date, created__lte=to_date).count()
            statistics.update({
                '4. Created Events': created_event_count,      
            })
        except:
            pass
        
        try:
            from cosinnus_note.models import Note
            created_note_count = Note.objects.filter(group__portal=CosinnusPortal.get_current(), created__gte=from_date, created__lte=to_date).count()
            statistics.update({
                '5. Created News': created_note_count,      
            })
        except:
            pass
        statistics = sorted(statistics.iteritems())
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

