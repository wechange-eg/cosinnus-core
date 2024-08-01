# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import datetime
import json
import logging
import pickle
import random
import urllib.error
import urllib.parse
import urllib.request
from builtins import FileNotFoundError, range, str

from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail.message import EmailMessage
from django.db.models import Q
from django.http.response import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from cosinnus.core.mail import (
    render_notification_item_html_mail,
    send_html_mail_threaded,
    send_mail,
    send_mail_or_fail_threaded,
)
from cosinnus.models import MEMBERSHIP_ADMIN, MEMBERSHIP_PENDING
from cosinnus.models.group import (
    CosinnusGroup,
    CosinnusGroupMembership,
    CosinnusLocation,
    CosinnusPermanentRedirect,
    CosinnusPortal,
    CosinnusPortalMembership,
)
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.models.widget import WidgetConfig
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.dashboard import create_initial_group_widgets
from cosinnus.utils.group import get_cosinnus_group_model, get_default_user_group_slugs
from cosinnus.utils.group import move_group_content as move_group_content_utils
from cosinnus.utils.http import make_csv_response, make_xlsx_response
from cosinnus.utils.permissions import check_user_can_receive_emails, check_user_superuser
from cosinnus.utils.settings import get_obfuscated_settings_strings
from cosinnus.utils.user import (
    accept_user_tos_for_portal,
    filter_active_users,
    is_user_active,
)
from cosinnus.views.profile_deletion import delete_userprofile

logger = logging.getLogger('cosinnus')


def ensure_group_widgets(request=None):
    """Do some integrity checks and corrections.
    Currently doing:
        - Checking all groups and projects for missing widgets versus the default widget
            settings and adding missing widgets
    """
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    groups = get_cosinnus_group_model().objects.all()
    ret = ''
    for group in groups:
        ret += 'Checked group %s\n<br/>' % group.slug
        create_initial_group_widgets(None, group)
    if request:
        return HttpResponse(ret)
    else:
        return ret


def delete_spam_users(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    return HttpResponseBadRequest('This view is disabled now!')

    ret = ''
    user_csv = ''
    deleted_user_count = 0

    spam_users = (
        get_user_model()
        .objects.filter(date_joined__gt='2014-09-10')
        .filter(Q(email__contains='.pl') | Q(cosinnus_profile__website__contains='.pl') | Q(email__contains='makre'))
        .distinct()
    )

    for user in spam_users:
        user_groups = CosinnusGroup.objects.get_for_user(user)
        if len(user_groups) > 1:
            ret += '> Not deleting a user because he is in %d groups <br/>' % len(user_groups)
            continue

        breakadmin = False
        for group in user_groups:
            admins = CosinnusGroupMembership.objects.get_admins(group=group)
            if user.pk in admins:
                ret += '> Not deleting a user because he is admin in group %s' % group.slug
                breakadmin = True
                break
        if breakadmin:
            continue

        user_csv += '%(id)s,%(email)s,%(first_name)s,%(last_name)s<br/>' % user.__dict__
        deleted_user_count += 1
        if request.GET.get('commit', False) == 'true':
            delete_userprofile(user)

    if not request.GET.get('commit', False) == 'true':
        ret = (
            ' **********   THIS IS A FAKE DELETION ONLY! user param ?commit=true to really delete the users! '
            '***********'
        )

    ret += '<br/><br/><br/>Deleted %d Users<br/><br/>' % deleted_user_count + user_csv
    return HttpResponse(ret)


def move_group_content(request, fromgroup, togroup):
    """access to function for moving group content from one group to another"""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    fromgroup = CosinnusGroup.objects.get_cached(slugs=fromgroup)
    togroup = CosinnusGroup.objects.get_cached(slugs=togroup)

    logs = move_group_content_utils(fromgroup, togroup)
    return HttpResponse('<br/>'.join(logs))


def recreate_all_group_widgets(request=None, verbose=False):
    """Resets all CosinnusGroup Dashboard Widget Configurations to their default
    by deleting and recreating them."""
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    # delete all widget configs
    WidgetConfig.objects.all().delete()

    # create all default widgets for all groups
    groups_ids = []
    all_groups = CosinnusGroup.objects.all()
    for group in all_groups:
        create_initial_group_widgets(None, group)
        groups_ids.append(str(group.id))
        if verbose:
            print(('>>> recreated widget config for group id', group.id))

    return HttpResponse('The following groups were updated:<br/><br/>' + '<br/>'.join(groups_ids))


HOUSEKEEPING_CACHE_KEY = 'cosinnus/core/housekeeping/setcache_debug'


def setcache(request, content):
    """set the cache with <content> /housekeeping/setcache/<content>/"""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    content = force_str(content)
    cache.set(HOUSEKEEPING_CACHE_KEY, content)
    return HttpResponse("Set '%s' as debug cache entry." % content)


def fillcache(request, number):
    """fills the cache with a list of random string uids"""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    try:
        number = int(number)
    except Exception:
        return HttpResponse('Argument given in URL must be a number!')

    content = ['XXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXx' for num in range(number)]
    cache.set(HOUSEKEEPING_CACHE_KEY, content)
    return HttpResponse('Set %d bytes as debug cache entry.' % len(pickle.dumps(content, -1)))


def getcache(request):
    """access to function for moving group content from one group to another"""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    cache_key = request.GET.get('key', HOUSEKEEPING_CACHE_KEY)
    content = cache.get(cache_key)
    return HttpResponse("The cache entry '%s' contains: '%s'." % (cache_key, content))


def deletecache(request):
    """access to function for moving group content from one group to another"""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    cache_key = request.GET.get('key', HOUSEKEEPING_CACHE_KEY)
    cache.delete(cache_key)
    return HttpResponse("The cache entry '%s' was deleted." % cache_key)


def test_logging(request, level='error'):
    harmless = 'my value'
    bic = 'shouldnotbeshown!bic'
    iban = 'shouldnotbeshown!iban'
    user_password_generated = 'shouldnotbeshown!pwd'
    extra = {
        'harmless': harmless,
        'bic': bic,
        'iban': iban,
        'user_password_generated': user_password_generated,
    }
    if level == 'exception':
        return 1 / 0
    if level in ['error', 'warning', 'info']:
        func = getattr(logger, level)
        func(f'Test logging event with level: {level}', extra=extra)
        return HttpResponse(f'Triggered a log message with level {level}.')
    return HttpResponse(f'Did not trigger a log event because level "{level}" was unknown.')


def check_and_delete_loop_redirects(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    delete = bool(request.GET.get('delete', False))

    bad_redirects = [redirect for redirect in CosinnusPermanentRedirect.objects.all() if not redirect.check_integrity()]
    response_string = 'Bad redirects:<br>' + '<br>'.join(
        [
            'portal: %d, from_slug: %s, from_type: %s'
            % (redirect.from_portal_id, redirect.from_slug, redirect.from_type)
            for redirect in bad_redirects
        ]
    )
    if delete:
        for redirect in bad_redirects:
            redirect.delete()
    response_string += '<br><br>' + (
        'These redirects were deleted.' if delete else 'Delete them by using ?delete=1 as GET!'
    )
    return HttpResponse(response_string)


def add_members_to_forum(request=None):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    str = 'Added these users:<br/><br/>\n'

    for portal in CosinnusPortal.objects.all():
        users = get_user_model().objects.filter(id__in=portal.members)
        for group_slug in get_default_user_group_slugs():
            try:
                group = CosinnusGroup.objects.get(slug=group_slug, portal_id=portal.id)
                for user in users:
                    memb, created = CosinnusGroupMembership.objects.get_or_create(
                        user=user, group=group, defaults={'status': MEMBERSHIP_MEMBER}
                    )
                    if not created:
                        if memb.status == MEMBERSHIP_PENDING:
                            memb.status = MEMBERSHIP_MEMBER
                            memb.save()
                            str += 'Set user %d to not pending anymore in portal %d <br/>\n' % (user.id, portal.id)
                    else:
                        str += 'Added user %d to forum in portal %d<br/>\n' % (user.id, portal.id)

            except CosinnusGroup.DoesNotExist:
                str += 'Could not find forum in portal %d <br/>\n' % portal.id

    return HttpResponse(str)


easter_european_country_codes = ['BY', 'BG', 'CZ', 'HU', 'MD', 'PL', 'RO', 'RU', 'SK', 'UA']


def user_statistics(request=None):
    if request and not check_user_superuser(request.user):
        return HttpResponseForbidden('Not authenticated')

    user_locs = (
        get_user_model()
        .objects.filter(cosinnus_profile__media_tag__location_lat__isnull=False)
        .values_list('id', 'cosinnus_profile__media_tag__location_lat', 'cosinnus_profile__media_tag__location_lon')
    )

    results = []

    class Found(Exception):
        pass

    for id, lat, lon in user_locs:
        location_url = 'http://maps.googleapis.com/maps/api/geocode/json?latlng=%f,%f' % (lat, lon)
        location_data = json.load(urllib.request.urlopen(location_url))
        try:
            for r in location_data['results']:
                for c in r['address_components']:
                    if 'country' in c['types']:
                        short_name = c['short_name']
                        if short_name in easter_european_country_codes:
                            results.append('%d,%f,%f,%s' % (id, lat, lon, short_name))
                            raise Found
        except Found:
            pass
    # group_locs = CosinnusGroup.objects.filter(locations__gt=0).values_list(
    #   'id', 'media_tag__location_lat', 'media_tag__location_lon')

    # user_locs_str = [str(x) for x in results]
    # group_locs_str = [str(y) for y in group_locs]

    return HttpResponse('<br/>'.join(results))  # + ' (group)<br/>'.join(group_locs_str))


def create_map_test_entities(request=None, count=1):
    """
    Creates <count> CosinnusProjects, CosinnusSocieties, Users and Events (in the created group), all with random
    coordinates
    """
    if not settings.DEBUG or (request and not request.user.is_superuser):
        return HttpResponseForbidden('Not allowed. System needs to be in DEBUG mode and you need to be admin!')

    from cosinnus_event.models import Event

    locs = [
        "Dr. Evil's hidden lair",
        'Bermuda Triangle',
        'Wardrobe to Narnia',
        'Platform 9 3/4',
        'Illuminati HQ',
        'Where I put my damn car keys',
        "Carmen and Waldo's cuddle cave",
    ]

    count = int(count)

    projnum = CosinnusProject.objects.all().count()
    groupnum = CosinnusSociety.objects.all().count()
    usernum = get_user_model().objects.all().count()
    eventnum = Event.objects.all().count()

    print(('>>> creating', count, 'Projects, Groups, Events and Users'))
    for i in range(count):
        projnum += 1
        groupnum += 1
        usernum += 1
        eventnum += 1
        proj = CosinnusProject.objects.create(
            name='MapProject #%d' % projnum, public=True, description='Test description'
        )
        group = CosinnusSociety.objects.create(
            name='MapGroup #%d' % groupnum, public=True, description='Test description'
        )
        user = get_user_model().objects.create(
            username='mapuser%d' % usernum,
            first_name='MapUser #%d' % usernum,
            email='testuser%d@nowhere.com' % usernum,
            is_active=True,
            last_login=now(),
        )
        CosinnusPortalMembership.objects.create(group=CosinnusPortal.get_current(), user=user, status=1)
        accept_user_tos_for_portal(user)
        event = Event.objects.create(
            group=proj,
            creator=user,
            title='MapEvent #%d' % eventnum,
            note='Test description',
            state=1,
            from_date=datetime.datetime(2099, 1, 1),
            to_date=datetime.datetime(2099, 1, 3),
        )

        locproj = CosinnusLocation.objects.create(group=proj)
        locgroup = CosinnusLocation.objects.create(group=group)

        mts = [locproj, locgroup, user.cosinnus_profile.media_tag, event.media_tag]
        for mt in mts:
            if hasattr(mt, 'visibility'):
                # set all media_tags to public
                mt.visibility = BaseTagObject.VISIBILITY_ALL
            # set random coord
            random.shuffle(locs)
            mt.location = locs[0]
            mt.location_lat = random.uniform(-60, 60)
            mt.location_lon = random.uniform(-160, 160)
            mt.save()

        print(('> Created', i + 1, '/', count, 'Projects, Groups, Events and Users'))

    return HttpResponse('Done. Created %d Projects, Groups, Events and Users' % count)


def reset_user_tos_flags(request=None):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    if not request.GET.get('confirm', False) == '1':
        active_users = filter_active_users(get_user_model().objects.all())
        ret = (
            "********** This will reset all %d active users' ToS accepted flag! Use param ?confirm=1 to delete the "
            'flags! ***********'
        ) % active_users.count()
    else:
        count = 0
        active_users = filter_active_users(get_user_model().objects.all())
        for profile in get_user_profile_model().objects.all().filter(user__in=active_users):
            profile.tos_accepted = False
            profile.save(update_fields=['tos_accepted'])
            count += 1
        ret = 'Successfully reset the ToS flag for %d users.' % count

    return HttpResponse(ret)


def send_testmail(request):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    mode = request.GET.get('mode', None)
    if mode not in ['html', 'direct', 'direct_html', 'threaded', 'override']:
        mode = 'html'

    subject = mode + ': Testmail from Housekeeping at %s' % str(now())
    template = 'cosinnus/common/internet_explorer_not_supported.html'
    retmsg = '\n\n<br><br> Use ?mode=[html, direct, direct_html, threaded, override]\n\nThe Answer was: '

    if mode == 'html':
        retmsg += force_str(
            send_html_mail_threaded(request.user, subject, textfield('This is a test mail from housekeeping.'))
        )
        return HttpResponse('Sent mail using html mode. ' + retmsg)
    if mode == 'direct':
        retmsg += force_str(send_mail(request.user.email, subject, template, {}))
        return HttpResponse('Sent mail using direct mode. ' + retmsg)
    if mode == 'direct_html':
        template = 'cosinnus/housekeeping/test_html_mail.html'
        retmsg += force_str(send_mail(request.user.email, subject, template, {}, is_html=True))
        return HttpResponse('Sent mail using direct HTML mode. ' + retmsg)
    if mode == 'threaded':
        retmsg += force_str(send_mail_or_fail_threaded(request.user.email, subject, template, {}))
        return HttpResponse('Sent mail using threaded mode. ' + retmsg)
    if mode == 'override':
        retmsg += force_str(
            EmailMessage(
                subject, 'No content', 'Testing <%s>' % settings.COSINNUS_DEFAULT_FROM_EMAIL, [request.user.email]
            ).send()
        )
        return HttpResponse('Sent mail using override mode. ' + retmsg)

    return HttpResponse('Did not send any mail. ' + retmsg)


def print_testmail(request):
    """Displays a HTML email like it would be sent to a user"""
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    subject = 'This is a test mail'

    content_html = textfield('Detailed testmail test content cannot be shown without a forum group.')

    forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
    if forum_slug:
        from cosinnus_notifications.models import NotificationEvent  # noqa
        from cosinnus_note.models import Note, Comment  # noqa
        from cosinnus_notifications.notifications import render_digest_item_for_notification_event

        forum = get_object_or_None(get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current())
        notes = Note.objects.filter(group=forum)
        if notes.count() > 0:
            note = notes[0]
            comment = Comment(creator=request.user, text='This is a test comment.', note=note)
            notification_event = NotificationEvent()
            notification_event._target_object = comment
            notification_event.group = forum
            notification_event.notification_id = 'note__note_comment_posted_on_any'
            notification_event.user = request.user
            content_html = render_digest_item_for_notification_event(notification_event)

    html = render_notification_item_html_mail(request.user, subject, content_html)
    return HttpResponse(html)


def _print_testdigest(request, digest_setting=None):
    """Displays a HTML email like it would be sent to a user"""
    if not request or not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    from cosinnus_notifications.models import NotificationEvent, UserNotificationPreference  # noqa
    from cosinnus_note.models import Note, Comment  # noqa
    from cosinnus_notifications.digest import send_digest_for_current_portal, _get_digest_email_context  # noqa

    if not digest_setting:
        digest_setting = UserNotificationPreference.SETTING_DAILY
    template = '/cosinnus/html_mail/digest.html'
    user_id = request.GET.get('user')
    if user_id:
        user = get_user_model().objects.filter(id=user_id).first()
    else:
        user = request.user
    if not user:
        return HttpResponse('No user supplied or user not found.')
    digest_html = send_digest_for_current_portal(digest_setting, debug_run_for_user=user)
    context = _get_digest_email_context(user, mark_safe(digest_html), now(), digest_setting)
    html = render_to_string(template, context=context)
    return HttpResponse(html)


def print_testdigest_daily(request):
    """Displays a HTML email like it would be sent to a user"""
    from cosinnus_notifications.models import UserNotificationPreference  # noqa

    return _print_testdigest(request, digest_setting=UserNotificationPreference.SETTING_DAILY)


def print_testdigest_weekly(request):
    """Displays a HTML email like it would be sent to a user"""
    from cosinnus_notifications.models import UserNotificationPreference  # noqa

    return _print_testdigest(request, digest_setting=UserNotificationPreference.SETTING_WEEKLY)


def print_settings(request):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    setts = ''
    obfuscated_settings = get_obfuscated_settings_strings()
    for key, val in obfuscated_settings.items():
        setts += '%s = %s<br/>' % (key, val)
    if not request:
        return setts
    return HttpResponse(
        f'Portal {settings.COSINNUS_PORTAL_NAME} is running cosinnus version {settings.COSINNUS_VERSION}. '
        f'Configured settings are:<br/><br/>' + setts
    )


def _get_group_storage_space_mb(group):
    size = 0
    for f in group.cosinnus_file_fileentry_set.all():
        if f.file:
            try:
                size += f.file.size
            except FileNotFoundError:
                pass
    size = size * 0.00000095367431640625  # in Mb
    return size


def group_storage_info(request):
    if request and not check_user_superuser(request.user):
        return HttpResponseForbidden('Not authenticated')

    prints = '<h1>All groups and projects with file storage usage over 10MB:</h1><br/>'
    for group in CosinnusGroup.objects.all():
        size = _get_group_storage_space_mb(group)
        if size > 10:
            prints += '- %s (%s): %i MB<br/>' % (group.name, group.slug, size)

    return HttpResponse(prints)


def newsletter_users(
    request,
    includeOptedOut=False,
    never_logged_in_only=False,
    all_portal_users=False,
    file_name='newsletter-user-emails',
):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    if not getattr(settings, 'COSINNUS_ENABLE_ADMIN_EMAIL_CSV_DOWNLOADS', False):
        return HttpResponseForbidden('This Feature is currently not enabled!')

    headers = [
        'email',
        'firstname',
        'lastname',
        'registration_timestamp',
        'language',
        'visitor_mtag_slugs',
    ]
    result_columns = [
        headers,
    ]
    portal = CosinnusPortal.get_current()

    if all_portal_users:
        # this gets users even when they don't have a portal membership yet
        users = get_user_model().objects.filter(is_active=True)
        if never_logged_in_only:
            users = users.filter(last_login__exact=None)
        else:
            users = users.exclude(last_login__exact=None)
    else:
        memberships = CosinnusPortalMembership.objects.filter(group=portal, user__is_active=True)
        if never_logged_in_only:
            memberships = memberships.filter(user__last_login__exact=None)
        else:
            memberships = memberships.exclude(user__last_login__exact=None)
        memberships = memberships.prefetch_related('user')
        users = [membership.user for membership in memberships]

    for user in users:
        if includeOptedOut or (
            check_user_can_receive_emails(user)
            and user.cosinnus_profile.settings.get('newsletter_opt_in', False) is True
        ):
            if never_logged_in_only or is_user_active(user):
                row = [
                    user.email,
                    user.first_name,
                    user.last_name,
                    user.date_joined,
                    user.cosinnus_profile.language,
                    ','.join([tag.slug for tag in user.cosinnus_profile.get_managed_tags()]),  #'visitor_mtag_slugs',
                ]
                result_columns.append(row)
    return make_xlsx_response(result_columns, file_name=file_name)


def active_user_emails(request):
    return newsletter_users(request, includeOptedOut=True, file_name='active-user-emails')


def never_logged_in_user_emails(request):
    return newsletter_users(
        request,
        includeOptedOut=True,
        never_logged_in_only=True,
        all_portal_users=True,
        file_name='never-logged-in-user-emails',
    )


def group_admin_emails(request, slugs):
    """For a comma-seperated list of group slugs, return a CSV of all emails
    of all admins of the groups.
    Will only return emails of users who CAN receive emails and
    who want to receive the newsletter"""
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    slugs = slugs.split(',')
    slugs = [slug.strip() for slug in slugs if len(slug.strip()) > 0]

    user_mails = []
    file_name = 'group-admin-user-emails'
    includeOptedOut = request.GET.get('includeOptedOut', False) == '1'
    portal = CosinnusPortal.get_current()
    memberships = (
        CosinnusGroupMembership.objects.filter(
            group__portal=portal, group__slug__in=slugs, status=MEMBERSHIP_ADMIN, user__is_active=True
        )
        .exclude(user__last_login__exact=None)
        .prefetch_related('user')
    )

    for membership in memberships:
        user = membership.user
        if check_user_can_receive_emails(user) and (
            includeOptedOut or user.cosinnus_profile.settings.get('newsletter_opt_in', False) is True
        ):
            user_mails.append(user.email)
    user_mails = list(set(user_mails))
    user_mails = [[user_mail] for user_mail in user_mails]

    return make_csv_response(user_mails, file_name=file_name)


def portal_switches_and_settings(request, file_name='portal-switches-and-settings'):
    """Returns a downloadable excel spreadsheet of all the settings in conf.py,
    including their comments and default values.
    Will ignore any setting with the tag #internal in its comments."""

    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    headers = [
        'Switch names',
        'Default values',
        'Commentary',
    ]

    import inspect

    import cosinnus.conf as cosconf

    data = inspect.getsourcelines(cosconf)[0]

    switch_names = []
    default_values = {}
    collected_comment = ''
    comments = {}

    skip_next = False
    for line in data:
        line = line.strip()
        # getting comments
        if line.startswith('#'):
            comment = line.split('#', 1)[1].strip()
            if '#internal' in comment:
                skip_next = True
            if comment:
                collected_comment += comment + ' '
        # getting switches
        if not line.startswith('#') and '=' in line:
            switch_name, switch_value = line.split('=', 1)
            switch_name = switch_name.strip()
            switch_value = switch_value.strip()
            if switch_name and switch_name.isupper():
                # if this is an internal switch we skip it
                if skip_next:
                    skip_next = False
                    collected_comment = ''
                    continue

                switch_names.append(switch_name)
                if switch_value in ('[', '(', '{'):
                    switch_value = '(object)'
                default_values[switch_name] = switch_value
                # putting comments to dict to bound each comment with its switch
                if collected_comment:
                    comments[switch_name] = collected_comment
                    collected_comment = ''

    # 'COSINNUS_' prefix  should be applied only to switches bounded with the `CosinnusConf` class
    rows = [
        [f'COSINNUS_{switch_name}', default_values.get(switch_name), comments.get(switch_name, '')]
        if hasattr(cosconf.CosinnusConf, switch_name)
        else [switch_name, default_values.get(switch_name), comments.get(switch_name, '')]
        for switch_name in switch_names
    ]

    return make_xlsx_response(rows=rows, row_names=headers, file_name=file_name)
