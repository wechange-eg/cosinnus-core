# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse, resolve, Resolver404
from django.utils.formats import get_format
from django.utils.translation import get_language

from cosinnus.conf import settings as SETTINGS
from cosinnus.core.registries import app_registry
from cosinnus.models.serializers.profile import UserSimpleSerializer
from postman.models import Message
import json
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.models.group import CosinnusPortal


def settings(request):
    return {
        'SETTINGS': SETTINGS,
    }


def cosinnus(request):
    """
    Exposes a set of global variables to the template rendering context:

    ``COSINNUS_BASE_URL``
        The index URL where cosinnus is being registered.

    ``COSINNUS_CURRENT_APP``
        If the current request points to a cosinnus (app) view, the name the
        app has been registered with (e.g. ``"todo"`` for "cosinnus_todo"). If
        not it is an empty string ``''``.

    ``COSINNUS_DATE_FORMAT``

    ``COSINNUS_DATETIME_FORMAT``
    
    ``COSINNUS_TIME_FORMAT``
    
    ``COSINNUS_DJANGO_DATETIME_FORMAT``
    
    ``COSINNUS_DJANGO_DATE_FORMAT``
    
    ``COSINNUS_DJANGO_DATE_SHORT_FORMAT``
    
    ``COSINNUS_COSINNUS_DJANGO_DATE_SHORT_CLEAR_FORMAT``
    
    ``COSINNUS_DJANGO_TIME_FORMAT``
    
    ``COSINNUS_USER``
        If ``request.user`` is logged in, its a serialized version of
        :class:`~cosinnus.models.serializers.profile.UserSimpleSerializer`. If
        not authenticated it is ``False``. Both serialized to JSON.
    """
    base_url = CosinnusPortal.get_current().get_domain() 
    base_url += '' if base_url[-1] == '/' else '/'

    user = request.user
    if user.is_authenticated():
        user_json = json.dumps(UserSimpleSerializer(user).data)
        unread_count = Message.objects.inbox_unread_count(user)
        from cosinnus_stream.models import Stream
        stream_unseen_count = Stream.objects.my_stream_unread_count(user)
    else:
        user_json = json.dumps(False)
        unread_count = 0
        stream_unseen_count = 0

    current_app_name = ''
    try:
        current_app = resolve(request.path.strip()).app_name
        current_app_name = app_registry.get_name(current_app)
    except KeyError:
        pass  # current_app is not a cosinnus app
    except Resolver404:
        pass
    
    return {
        'COSINNUS_BASE_URL': base_url,
        'COSINNUS_CURRENT_APP': current_app_name,
        'COSINNUS_DATE_FORMAT': get_format('COSINNUS_DATETIMEPICKER_DATE_FORMAT'),
        'COSINNUS_DATETIME_FORMAT': get_format('COSINNUS_DATETIMEPICKER_DATETIME_FORMAT'),
        'COSINNUS_TIME_FORMAT': get_format('COSINNUS_DATETIMEPICKER_TIME_FORMAT'),
        'COSINNUS_DJANGO_DATETIME_FORMAT': get_format('COSINNUS_DJANGO_DATETIME_FORMAT'),
        'COSINNUS_DJANGO_DATE_FORMAT': get_format('COSINNUS_DJANGO_DATE_FORMAT'),
        'COSINNUS_DJANGO_DATE_SHORT_FORMAT': get_format('COSINNUS_DJANGO_DATE_SHORT_FORMAT'),
        'COSINNUS_DJANGO_DATE_SHORT_CLEAR_FORMAT': get_format('COSINNUS_DJANGO_DATE_SHORT_CLEAR_FORMAT'),
        'COSINNUS_DJANGO_TIME_FORMAT': get_format('COSINNUS_DJANGO_TIME_FORMAT'),
        'COSINNUS_USER': user_json,
        'COSINNUS_UNREAD_MESSAGE_COUNT': unread_count,
        'COSINNUS_STREAM_UNSEEN_COUNT': stream_unseen_count,
        'COSINNUS_CURRENT_LANGUAGE': get_language(),
        'COSINNUS_CURRENT_PORTAL': CosinnusPortal.get_current(),
    }
