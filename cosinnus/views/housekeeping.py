# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from builtins import str, FileNotFoundError
from builtins import range
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership,\
    CosinnusPermanentRedirect, CosinnusPortal, CosinnusPortalMembership, CosinnusLocation
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.models import MEMBERSHIP_PENDING, MEMBERSHIP_ADMIN
from cosinnus.utils.dashboard import create_initial_group_widgets
from django.http.response import HttpResponse, HttpResponseForbidden,\
    HttpResponseBadRequest
from django.contrib.auth import get_user_model
from django.db.models import Q
from cosinnus.views.profile import delete_userprofile
from cosinnus.utils.group import move_group_content as move_group_content_utils,\
    get_default_user_group_slugs, get_cosinnus_group_model
from cosinnus.models.widget import WidgetConfig
from django.core.cache import cache
from django.conf import settings
import json
import urllib.request, urllib.error, urllib.parse
from django.utils.encoding import force_text
import pickle
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety,\
    CosinnusConference
import datetime
from cosinnus.models.tagged import BaseTagObject
import random
from django.utils.timezone import now
from cosinnus.utils.user import filter_active_users, accept_user_tos_for_portal,\
    get_user_tos_accepted_date, is_user_active, get_user_id_hash
from cosinnus.models.profile import get_user_profile_model
from django.core.mail.message import EmailMessage
from cosinnus.core.mail import send_mail,\
    send_mail_or_fail_threaded, send_html_mail_threaded,\
    render_notification_item_html_mail
from django.template.defaultfilters import linebreaksbr
from django.db.models.aggregates import Count
from cosinnus.utils.http import make_csv_response, make_xlsx_response
from operator import itemgetter
from cosinnus.utils.permissions import check_user_can_receive_emails,\
    check_user_superuser, check_user_portal_manager
import logging
from cosinnus.templatetags.cosinnus_tags import textfield
from annoying.functions import get_object_or_None
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

logger = logging.getLogger('cosinnus')


def ensure_group_widgets(request=None):
    """ Do some integrity checks and corrections. 
        Currently doing:
            - Checking all groups and projects for missing widgets versus the default widget
                settings and adding missing widgets
    """
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    groups = get_cosinnus_group_model().objects.all()
    ret = ""
    for group in groups:
        ret += "Checked group %s\n<br/>" % group.slug
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
    
    spam_users = get_user_model().objects.filter(date_joined__gt='2014-09-10').filter(
        Q(email__contains='.pl') | Q(cosinnus_profile__website__contains='.pl') | Q(email__contains='makre')
    ).distinct()
    
    
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
        ret = ' **********   THIS IS A FAKE DELETION ONLY! user param ?commit=true to really delete the users! ***********'
    
    ret += '<br/><br/><br/>Deleted %d Users<br/><br/>' % deleted_user_count + user_csv
    return HttpResponse(ret)


def move_group_content(request, fromgroup, togroup):
    """ access to function for moving group content from one group to another """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    fromgroup = CosinnusGroup.objects.get_cached(slugs=fromgroup)
    togroup = CosinnusGroup.objects.get_cached(slugs=togroup)
    
    logs = move_group_content_utils(fromgroup, togroup)
    return HttpResponse("<br/>".join(logs))
        
        
def recreate_all_group_widgets(request=None, verbose=False):
    """ Resets all CosinnusGroup Dashboard Widget Configurations to their default
        by deleting and recreating them. """
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
            print((">>> recreated widget config for group id", group.id))
    
    return HttpResponse("The following groups were updated:<br/><br/>" + "<br/>".join(groups_ids))


HOUSEKEEPING_CACHE_KEY = 'cosinnus/core/housekeeping/setcache_debug'

def setcache(request, content):
    """ set the cache with <content> /housekeeping/setcache/<content>/ """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    content = force_text(content)
    cache.set(HOUSEKEEPING_CACHE_KEY, content)
    return HttpResponse("Set '%s' as debug cache entry." % content)
        
def fillcache(request, number):
    """ fills the cache with a list of random string uids """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    try:
        number = int(number)
    except:
        return HttpResponse("Argument given in URL must be a number!")
    
    content = ['XXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXxXXXx' for num in range(number)]
    cache.set(HOUSEKEEPING_CACHE_KEY, content)
    return HttpResponse("Set %d bytes as debug cache entry." % len(pickle.dumps(content, -1)))
        
        
def getcache(request):
    """ access to function for moving group content from one group to another """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    cache_key = request.GET.get('key', HOUSEKEEPING_CACHE_KEY)
    content = cache.get(cache_key)
    return HttpResponse("The cache entry '%s' contains: '%s'." % (cache_key, content))

        
def deletecache(request):
    """ access to function for moving group content from one group to another """
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
        return 1/0
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
    response_string = 'Bad redirects:<br>' +  \
            '<br>'.join([ \
                'portal: %d, from_slug: %s, from_type: %s' % (redirect.from_portal_id, redirect.from_slug, redirect.from_type) \
             for redirect in bad_redirects])
    if delete:
        for redirect in bad_redirects:
            redirect.delete()
    response_string += '<br><br>' + ('These redirects were deleted.' if delete else 'Delete them by using ?delete=1 as GET!')
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
                    memb, created = CosinnusGroupMembership.objects.get_or_create(user=user, group=group, defaults={'status': MEMBERSHIP_MEMBER})
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
    
    user_locs = get_user_model().objects.filter(cosinnus_profile__media_tag__location_lat__isnull=False)\
        .values_list('id', 'cosinnus_profile__media_tag__location_lat', 'cosinnus_profile__media_tag__location_lon')
    
    results = []
    
    class Found(Exception): pass
    for id, lat, lon in user_locs:
        location_url = "http://maps.googleapis.com/maps/api/geocode/json?latlng=%f,%f" % (lat, lon)
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
    #group_locs = CosinnusGroup.objects.filter(locations__gt=0).values_list('id', 'media_tag__location_lat', 'media_tag__location_lon')
    
    #user_locs_str = [str(x) for x in results]
    #group_locs_str = [str(y) for y in group_locs]
    
    return HttpResponse('<br/>'.join(results))# + ' (group)<br/>'.join(group_locs_str))


def create_map_test_entities(request=None, count=1):
    """ Creates <count> CosinnusProjects, CosinnusSocieties, Users and Events (in the created group), all with random coordinates """
    if not settings.DEBUG or (request and not request.user.is_superuser):
        return HttpResponseForbidden('Not allowed. System needs to be in DEBUG mode and you need to be admin!')
    
    from cosinnus_event.models import Event
    locs = ['Dr. Evil\'s hidden lair', 'Bermuda Triangle', 'Wardrobe to Narnia', 'Platform 9 3/4', 
            'Illuminati HQ', 'Where I put my damn car keys', 'Carmen and Waldo\'s cuddle cave']
    
    count = int(count)
    
    projnum = CosinnusProject.objects.all().count()
    groupnum = CosinnusSociety.objects.all().count()
    usernum = get_user_model().objects.all().count()
    eventnum = Event.objects.all().count()
    
    print((">>> creating", count, "Projects, Groups, Events and Users"))
    for i in range(count):
        projnum += 1
        groupnum += 1
        usernum += 1
        eventnum += 1
        proj = CosinnusProject.objects.create(name='MapProject #%d' % projnum, public=True, description='Test description')
        group = CosinnusSociety.objects.create(name='MapGroup #%d' % groupnum, public=True, description='Test description')
        user = get_user_model().objects.create(username='mapuser%d' % usernum, first_name='MapUser #%d' % usernum,
            email='testuser%d@nowhere.com' % usernum, is_active=True, last_login=now())
        CosinnusPortalMembership.objects.create(group=CosinnusPortal.get_current(), user=user, status=1)
        accept_user_tos_for_portal(user)
        event = Event.objects.create(group=proj, creator=user, title='MapEvent #%d' % eventnum, note='Test description', 
            state=1, from_date=datetime.datetime(2099, 1, 1), to_date=datetime.datetime(2099, 1, 3))
        
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
            
        print(("> Created", i+1, "/", count, "Projects, Groups, Events and Users"))
        
    return HttpResponse("Done. Created %d Projects, Groups, Events and Users" % count)

def delete_portal(portal_slug):
    """ Completely deletes a portal object and all of its groups and all objects assigned to the groups.
        THen deletes (!) any users who are both no member of any group AND no member of any portal. """
    # do NOT delete etherpads on the server!
    settings.COSINNUS_DELETE_ETHERPADS_ON_SERVER_ON_DELETE = False
    CosinnusPortal.objects.get(slug=portal_slug).delete()
    get_user_model().objects.filter(cosinnus_memberships__isnull=True).filter(cosinnus_portal_memberships__isnull=True).delete()



def reset_user_tos_flags(request=None):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')

    if not request.GET.get('confirm', False) == '1':
        active_users = filter_active_users(get_user_model().objects.all())
        ret = '********** This will reset all %d active users\' ToS accepted flag! Use param ?confirm=1 to delete the flags! ***********' % active_users.count()
    else:
        count = 0
        active_users = filter_active_users(get_user_model().objects.all())
        for profile in get_user_profile_model().objects.all().filter(user__in=active_users):
            del profile.settings['tos_accepted']
            profile.save(update_fields=['settings'])
            count += 1
        ret = 'Successfully reset the ToS flag for %d users.' % count
        
    return HttpResponse(ret)


def send_testmail(request):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    mode = request.GET.get('mode', None)
    if mode not in ['html', 'direct', 'direct_html', 'threaded', 'override']:
        mode = 'html'
    
    subject =  mode + ': Testmail from Housekeeping at %s' % str(now())
    template = 'cosinnus/common/internet_explorer_not_supported.html'
    retmsg = '\n\n<br><br> Use ?mode=[html, direct, direct_html, threaded, override]\n\nThe Answer was: '
    
    if mode == 'html':
        retmsg += force_text(send_html_mail_threaded(request.user, subject, textfield('This is a test mail from housekeeping.')))
        return HttpResponse('Sent mail using html mode. ' + retmsg)
    if mode == 'direct':
        retmsg += force_text(send_mail(request.user.email, subject, template, {}))
        return HttpResponse('Sent mail using direct mode. ' + retmsg)
    if mode == 'direct_html':
        template = 'cosinnus/housekeeping/test_html_mail.html'
        retmsg += force_text(send_mail(request.user.email, subject, template, {}, is_html=True))
        return HttpResponse('Sent mail using direct HTML mode. ' + retmsg)
    if mode == 'threaded':
        retmsg += force_text(send_mail_or_fail_threaded(request.user.email, subject, template, {}))
        return HttpResponse('Sent mail using threaded mode. ' + retmsg)
    if mode == 'override':
        retmsg += force_text(EmailMessage(subject, 'No content', 'Testing <%s>' % settings.COSINNUS_DEFAULT_FROM_EMAIL, [request.user.email]).send())
        return HttpResponse('Sent mail using override mode. ' + retmsg)
        
    return HttpResponse('Did not send any mail. ' + retmsg)


def print_testmail(request):
    """ Displays a HTML email like it would be sent to a user """
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    subject =  'This is a test mail'
    
    content_html = textfield("Detailed testmail test content cannot be shown without a forum group.")
    
    forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
    if forum_slug:
        from cosinnus_notifications.models import NotificationEvent # noqa
        from cosinnus_note.models import Note, Comment # noqa
        from cosinnus_notifications.notifications import render_digest_item_for_notification_event
        
        forum = get_object_or_None(get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current())
        notes = Note.objects.filter(group=forum)
        if notes.count() > 0:
            note = notes[0]
            comment = Comment(creator=request.user, text="This is a test comment.", note=note)
            notification_event = NotificationEvent()
            notification_event._target_object = comment
            notification_event.group = forum
            notification_event.notification_id = 'note__note_comment_posted_on_any'
            notification_event.user = request.user
            content_html = render_digest_item_for_notification_event(notification_event)
        
    html = render_notification_item_html_mail(request.user, subject, content_html)
    return HttpResponse(html)


def print_testdigest(request):
    """ Displays a HTML email like it would be sent to a user """
    if not request or not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    from cosinnus_notifications.models import NotificationEvent, UserNotificationPreference # noqa
    from cosinnus_note.models import Note, Comment # noqa
    from cosinnus_notifications.digest import send_digest_for_current_portal, _get_digest_email_context # noqa
    
    digest_setting = UserNotificationPreference.SETTING_WEEKLY
    template = '/cosinnus/html_mail/digest.html'
    digest_html = send_digest_for_current_portal(digest_setting, debug_run_for_user=request.user)
    context = _get_digest_email_context(request.user, mark_safe(digest_html), now(), digest_setting)
    html = render_to_string(template, context=context)
    return HttpResponse(html)


def print_settings(request):
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    setts = ''
    for key in dir(settings):
        val = force_text(getattr(settings, key))
        if 'password' in key.lower() or 'password' in val.lower() or  \
                'secret' in key.lower() or 'secret' in val.lower():
            val = '***'
        setts += '%s = %s<br/>' % (key, val)
    return HttpResponse('Settings are:<br/>' + setts)

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


def conference_storage_report_csv(request):
    """ See ``group_storage_report_csv``, this is the same, just for Conferences and their subprojects. """
    return group_storage_report_csv(request, group_model=CosinnusConference, filename='conference-storage-report')

def group_storage_report_csv(request, group_model=None, filename='group-storage-report'):
    """
        Will return a CSV containing infos about all Groups:
            URL, Member-count, Number-of-Projects, Storage-Size-in-MB, Storage-Size-of-Group-and-all-Child-Projects-in-MB
    """
    if request and not check_user_superuser(request.user) and not check_user_portal_manager(request.user):
        return HttpResponseForbidden('Not authenticated')
    
    rows = []
    headers = ['url', 'member-count', 'number-projects', 'group-storage-mb', 'group-and-projects-sum-mb']
    
    klass = group_model or CosinnusSociety
    for group in klass.objects.all_in_portal():
        projects = group.get_children()
        group_size = _get_group_storage_space_mb(group)
        projects_size = 0
        for project in projects:
            projects_size += _get_group_storage_space_mb(project)
        rows.append([group.get_absolute_url(), group.member_count, len(projects), group_size, group_size + projects_size])
    rows = sorted(rows, key=itemgetter(4), reverse=True)
    return make_csv_response(rows, headers, filename)


def project_storage_report_csv(request):
    """
        Will return a CSV containing infos about all Projects:
            URL, Member-count, Storage-Size-in-MB
    """
    if request and not check_user_superuser(request.user) and not check_user_portal_manager(request.user):
        return HttpResponseForbidden('Not authenticated')
    
    rows = []
    headers = ['url', 'member-count', 'project-storage-mb',]
    
    for project in CosinnusProject.objects.all_in_portal():
        project_size = _get_group_storage_space_mb(project)
        rows.append([project.get_absolute_url(), project.member_count, project_size])
    rows = sorted(rows, key=itemgetter(2), reverse=True)
    return make_csv_response(rows, headers, 'project-storage-report')

    
def user_activity_info(request):
    if request and not check_user_superuser(request.user) and not check_user_portal_manager(request.user):
        return HttpResponseForbidden('Not authenticated')
    
    prints = '<h1>User activity of users who logged in at least once, in terms of memberships in projects+groups, sorted by highest, one user per row:</h1><br/></br>'
    users = {}
    
    # this filtering simply does not work in django 1.8, the count subfilters are ignored
#     group_projects = Count('cosinnus_memberships', filter=Q(cosinnus_memberships__group__portal=CosinnusPortal.get_current()))
#     group_projects_admin = Count('cosinnus_memberships', filter=(Q(cosinnus_memberships__group__portal=CosinnusPortal.get_current()) & Q(cosinnus_memberships__status=MEMBERSHIP_ADMIN)))
#     projects_only = Count('cosinnus_memberships', filter=(Q(cosinnus_memberships__group__portal=CosinnusPortal.get_current()) & Q(cosinnus_memberships__group__type=CosinnusGroup().TYPE_PROJECT)))
#     groups_only = Count('cosinnus_memberships', filter=(Q(cosinnus_memberships__group__portal=CosinnusPortal.get_current()) & Q(cosinnus_memberships__group__type=CosinnusGroup().TYPE_SOCIETY)))
#     for user in get_user_model().objects.filter(is_active=True).exclude(last_login__exact=None).\
#                 annotate(group_projects=group_projects).annotate(group_projects_admin=group_projects_admin).\
#                 annotate(projects_only=projects_only).annotate(groups_only=groups_only):
    portal = CosinnusPortal.get_current()
    headers = [
        'user-hashed-id',
    ]
    offset = 1
    if settings.COSINNUS_CONFERENCES_ENABLED:
        headers += [
            'conferences-count',
            'admin-of-conferences-count',
        ]
        offset += 2
    headers += [
        'projects-and-groups-count',
        'groups-only-count',
        'projects-only-count',
        'admin-of-projects-and-groups-count',
        'user-last-authentication-login-days',
        'current-tos-accepted',
        'registration-date',
        'events-attended',
    ]
    group_type_cache = {} # id (int) --> group type (int)
    for membership in CosinnusGroupMembership.objects.filter(group__portal=CosinnusPortal.get_current(), user__is_active=True).exclude(user__last_login__exact=None):
        # get the statistics row for the user of the membership, if there already is one we're aggregating
        user_row = users.get(membership.user_id, None)
        if user_row is None:
            user = membership.user
            if not hasattr(user, 'cosinnus_profile'):
                continue
            initial_row = [
                get_user_id_hash(user),         # 'user-hashed-id'
            ]
            if settings.COSINNUS_CONFERENCES_ENABLED:
                initial_row += [
                    0,                          # 'conferences-count',
                    0,                          # 'admin-of-conferences-count',
                ]
            tos_accepted_date = get_user_tos_accepted_date(user)
            tos_accepted = 1
            if portal.tos_date.year > 2000 and (tos_accepted_date is None or tos_accepted_date < portal.tos_date):
                tos_accepted = 0
            initial_row += [
                0,                              # 'projects-and-groups-count',
                0,                              # 'groups-only-count',
                0,                              # 'projects-only-count',
                0,                              # 'admin-of-projects-and-groups-count',
                (now()-user.last_login).days,   # 'user-last-login-days',
                tos_accepted,                   # 'current-tos-accepted',
                user.date_joined,               # 'registration-date',
                0,                              # 'events-attended',
            ]
            user_row = initial_row
        
        group_type = group_type_cache.get(membership.group_id, None)
        if group_type is None:
            group_type = membership.group.type
            group_type_cache[membership.group_id] = group_type
            
        if settings.COSINNUS_CONFERENCES_ENABLED:
            if group_type == CosinnusGroup.TYPE_CONFERENCE:
                user_row[1] += 1 # 'conferences-count'
                if membership.status == MEMBERSHIP_ADMIN:
                    user_row[2] += 1 # 'admin-of-conferences-count',
        user_row[offset] += 1 # 'projects-and-groups-count'
        if group_type == CosinnusGroup.TYPE_PROJECT:
            user_row[offset+1] += 1 # 'groups-only-count'
        if group_type == CosinnusGroup.TYPE_SOCIETY:
            user_row[offset+2] += 1 # 'projects-only-count'
        if group_type in [CosinnusGroup.TYPE_SOCIETY, CosinnusGroup.TYPE_PROJECT] and membership.status == MEMBERSHIP_ADMIN:
            user_row[offset+3] += 1 # 'admin-of-projects-and-groups-count'
        
        users[membership.user_id] = user_row
    
    # add event attendance stats
    from cosinnus_event.models import EventAttendance # noqa
    for attendance in EventAttendance.objects.filter(state=EventAttendance.ATTENDANCE_GOING):
        user_row = users.get(attendance.user_id, None)
        if user_row is None:
            continue
        user_row[offset+7] += 1
    
    rows = users.values()
    rows = sorted(rows, key=lambda row: row[offset], reverse=True)

    #prints += '<br/>'.join([','.join((str(cell) for cell in row)) for row in rows])
    #return HttpResponse(prints)
    return make_csv_response(rows, headers, 'user-activity-report')


def newsletter_users(request, includeOptedOut=False, never_logged_in_only=False, 
                       all_portal_users=False, file_name='newsletter-user-emails'):
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
    result_columns = [headers,]
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
        if includeOptedOut or (check_user_can_receive_emails(user) and user.cosinnus_profile.settings.get('newsletter_opt_in', False) == True):
            if never_logged_in_only or is_user_active(user):
                row = [
                    user.email,
                    user.first_name,
                    user.last_name,
                    user.date_joined,
                    user.cosinnus_profile.language,
                    ','.join([tag.slug for tag in user.cosinnus_profile.get_managed_tags()]), #'visitor_mtag_slugs',
                ]
                result_columns.append(row)
    return make_xlsx_response(result_columns, file_name=file_name)

def active_user_emails(request):
    return newsletter_users(request, includeOptedOut=True, file_name='active-user-emails')

def never_logged_in_user_emails(request):
    return newsletter_users(request, includeOptedOut=True, never_logged_in_only=True,
                            all_portal_users=True, file_name='never-logged-in-user-emails')

def group_admin_emails(request, slugs):
    """ For a comma-seperated list of group slugs, return a CSV of all emails
        of all admins of the groups.
        Will only return emails of users who CAN receive emails and
        who want to receive the newsletter """
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
        
    slugs = slugs.split(',')
    slugs = [slug.strip() for slug in slugs if len(slug.strip()) > 0]
    
    user_mails = []
    file_name='group-admin-user-emails'
    includeOptedOut = request.GET.get('includeOptedOut', False) == '1'
    portal = CosinnusPortal.get_current()
    memberships = CosinnusGroupMembership.objects.filter(
            group__portal=portal, 
            group__slug__in=slugs,
            status=MEMBERSHIP_ADMIN,
            user__is_active=True
        ).exclude(user__last_login__exact=None).prefetch_related('user')
    
    for membership in memberships:
        user = membership.user
        if check_user_can_receive_emails(user) and (includeOptedOut or user.cosinnus_profile.settings.get('newsletter_opt_in', False) == True):
            user_mails.append(user.email)
    user_mails = list(set(user_mails))
    user_mails = [[user_mail] for user_mail in user_mails]
    
    return make_csv_response(user_mails, file_name=file_name)


def portal_switches_and_settings(request, file_name='portal-switches-and-settings'):
    """ Returns a downloadable excel spreadsheet of all the settings in conf.py, 
        including their comments and default values.
        Will ignore any setting with the tag #internal in its comments. """
        
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
    rows = [[f'COSINNUS_{switch_name}', default_values.get(switch_name), comments.get(switch_name, '')]
            if hasattr(cosconf.CosinnusConf, switch_name) 
            else [switch_name, default_values.get(switch_name), comments.get(switch_name, '')] 
            for switch_name in switch_names]
    
    return make_xlsx_response(rows=rows, row_names=headers, file_name=file_name)
