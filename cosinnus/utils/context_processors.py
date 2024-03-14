# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import resolve, Resolver404, reverse
from django.utils.formats import get_format
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings as SETTINGS
from cosinnus.core.registries import app_registry
from cosinnus.api.serializers.user import UserSerializer
import json
from cosinnus.models.group import CosinnusPortal
from cosinnus.forms.user import TermsOfServiceFormFields
from cosinnus.models.profile import GlobalBlacklistedEmail

import logging
from cosinnus.utils.user import get_user_tos_accepted_date,\
    check_user_has_accepted_portal_tos
from cosinnus.models.managed_tags import CosinnusManagedTag
from cosinnus.trans.group import get_group_trans_by_type
from cosinnus.utils.permissions import check_user_verified
from cosinnus.utils.version_history import get_version_history_for_user
from datetime import timedelta
from django.utils import timezone
from django.template.defaultfilters import date
logger = logging.getLogger('cosinnus')


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
        :class:`~cosinnus.api.serializers.user.UserSerializer`. If
        not authenticated it is ``False``. Both serialized to JSON.
    """
    base_url = CosinnusPortal.get_current().get_domain() 
    base_url += '' if base_url[-1] == '/' else '/'

    user = request.user
    if user.is_authenticated:
        user_json = json.dumps(UserSerializer(user).data)
    else:
        user_json = json.dumps(False)
    
    # we only need these expensive metrics for the old-style navbar
    if user.is_authenticated and not \
            (getattr(SETTINGS, 'COSINNUS_USE_V2_DASHBOARD', False) or \
                (getattr(SETTINGS, 'COSINNUS_USE_V2_NAVBAR_ADMIN_ONLY', False) and user.is_superuser)):
        if getattr(SETTINGS, 'COSINNUS_ROCKET_ENABLED', False):
            unread_count = 0
            stream_unseen_count = 0
            # since this is a locking request, we do not use rocketchat unread counters on page load
            #from cosinnus_message.rocket_chat import RocketChatConnection
            #unread_count = RocketChatConnection().unread_messages(user)
        else:
            from cosinnus_stream.models import Stream # noqa
            stream_unseen_count = Stream.objects.my_stream_unread_count(user)
            from postman.models import Message # noqa
            unread_count = Message.objects.inbox_unread_count(user)
    else:
        unread_count = 0
        stream_unseen_count = 0

    current_app_name = ''
    try:
        current_app = resolve(request.path.strip()).app_name.replace(':', '_')
        current_app_name = app_registry.get_name(current_app)
    except KeyError:
        pass  # current_app is not a cosinnus app
    except Resolver404:
        pass
    
    v3_api_content_active = bool(getattr(request, 'v3_api_content_active', None) == True)

    # version history
    if v3_api_content_active:
        version_history, version_history_unread_count = {}, 0
    else:
        version_history, version_history_unread_count = get_version_history_for_user(request.user)
    
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
        'COSINNUS_MANAGED_TAG_LABELS': CosinnusManagedTag.labels,
        'COSINNUS_PROJECT_TRANS': get_group_trans_by_type(0),
        'COSINNUS_SOCIETY_TRANS': get_group_trans_by_type(1),
        'COSINNUS_CONFERENCE_TRANS': get_group_trans_by_type(2),
        'COSINNUS_USER_TIMEZONE': user.is_authenticated and user.cosinnus_profile.timezone.zone or None,
        'COSINNUS_VERSION_HISTORY': version_history,
        'COSINNUS_VERSION_HISTORY_UNREAD_COUNT': version_history_unread_count,
        'COSINNUS_V3_API_CONTENT_ACTIVE': v3_api_content_active,
    }


def tos_check(request):
    """ Checks if the portal's ToS version is higher than those that the user
        has accepted, and if so, renders the `updated_tos_form` into the context.
        Currently, `extra_body_header.html` (from `base.html`) checks if the form
        is present and renders a modal popup with it. """
        
    portal = CosinnusPortal.get_current()
    user = request.user
    if user.is_authenticated:
        try:
            tos_accepted_date = get_user_tos_accepted_date(user)
            tos_were_updated = portal.tos_date.year > 2000 and (tos_accepted_date is None or tos_accepted_date < portal.tos_date)
            # if a portal's tos_date has never moved beyond the default, we don't check the tos_accepted_date, 
            # to maintain backwards compatibility with users who have only the `settings.tos_accepted` boolean
            if tos_were_updated or not check_user_has_accepted_portal_tos(user):
                updated_tos_form = TermsOfServiceFormFields(initial={
                    'newsletter_opt_in': user.cosinnus_profile.settings.get('newsletter_opt_in', False)
                })
                return {
                    'updated_tos_form': updated_tos_form, 
                }
        except Exception as e:
            logger.error('Error in `context_processory.tos_check`: %s' % e, extra={'exception': e})
    return {}


def email_verified(request):
    """ Add additional announcements to the context which are checked for in base.html. """
    context = dict()
    portal = CosinnusPortal.get_current()
    user = request.user

    if (user.is_authenticated and
            not user.is_guest and
            portal.email_needs_verification and
            not GlobalBlacklistedEmail.is_email_blacklisted(request.user.email) and
            not check_user_verified(request.user)):
        url = reverse('cosinnus:resend-email-validation')
        url = '{}?next={}'.format(url, request.path)
        msg = _('Please verify your email address.')
        # show ultimatum date until the nag-popup begins
        if SETTINGS.COSINNUS_USER_SHOW_EMAIL_VERIFIED_POPUP_AFTER_DAYS > 0:
            target_date = user.date_joined + timedelta(days=SETTINGS.COSINNUS_USER_SHOW_EMAIL_VERIFIED_POPUP_AFTER_DAYS)
            msg = _('Please verify your email address by %(date_string)s.') % {'date_string': date(timezone.localtime(target_date), 'SHORT_DATE_FORMAT')}
        
        msg += ' ' + _('Make sure your email address "%(email_address)s" is correct.') % {'email_address': user.email}
        link_label = _('Click here to receive an email with a verification link.')
        context['email_not_verified_announcement'] = {
            'level': 'warning',
            'text': f'{msg} <a href="{url}">{link_label}</a>'
        }
    elif user.is_authenticated and user.is_guest and request.path != reverse('cosinnus:guest-user-not-allowed'):
        msg = _('You are currently using the platform with a guest account provided to you by a link.')
        url = reverse('cosinnus:guest-user-not-allowed')
        link_label = _('More infos...')
        context['user_guest_announcement'] = {
            'level': 'info',
            'text': f'{msg} <a href="{url}">{link_label}</a>',
        }
    return context
