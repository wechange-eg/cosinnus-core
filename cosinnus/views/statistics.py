# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http.response import JsonResponse
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.utils.user import filter_active_users
from cosinnus.models.group import CosinnusPortal
from django.contrib.auth import get_user_model


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
