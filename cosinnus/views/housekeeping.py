# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership,\
    CosinnusPermanentRedirect, CosinnusPortal, MEMBERSHIP_MEMBER,\
    MEMBERSHIP_PENDING, CosinnusPortalMembership, CosinnusLocation
from cosinnus.utils.dashboard import create_initial_group_widgets
from django.http.response import HttpResponse, HttpResponseForbidden
from django.contrib.auth import get_user_model
from django.db.models import Q
from cosinnus.views.profile import delete_userprofile
from cosinnus.utils.group import move_group_content as move_group_content_utils
from cosinnus.models.widget import WidgetConfig
from django.core.cache import cache
from django.conf import settings
from cosinnus.conf import settings as cosinnus_settings
import json
import urllib2
from django.utils.encoding import force_text
from uuid import uuid4
import pickle
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
import datetime
from cosinnus.models.tagged import BaseTagObject
import random
from django.utils.timezone import now
from cosinnus.utils.user import filter_active_users
from cosinnus.models.profile import get_user_profile_model
from django.core.mail.message import EmailMessage
from cosinnus.core.mail import send_mail_or_fail, send_mail,\
    send_mail_or_fail_threaded


def housekeeping(request=None):
    """ Do some integrity checks and corrections. 
        Currently doing:
            - Checking all groups and projects for missing widgets versus the default widget
                settings and adding missing widgets
    """
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    groups = CosinnusGroup.objects.all()
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
            print ">>> recreated widget config for group id", group.id
    
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
        for group_slug in getattr(settings, 'NEWW_DEFAULT_USER_GROUPS', []):
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
    if request and not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    user_locs = get_user_model().objects.filter(cosinnus_profile__media_tag__location_lat__isnull=False)\
        .values_list('id', 'cosinnus_profile__media_tag__location_lat', 'cosinnus_profile__media_tag__location_lon')
    
    results = []
    
    class Found(Exception): pass
    for id, lat, lon in user_locs:
        location_url = "http://maps.googleapis.com/maps/api/geocode/json?latlng=%f,%f" % (lat, lon)
        location_data = json.load(urllib2.urlopen(location_url))
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
    
    print ">>> creating", count, "Projects, Groups, Events and Users"
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
        user.cosinnus_profile.settings['tos_accepted'] = 'true'
        user.cosinnus_profile.save()
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
            
        print "> Created", i+1, "/", count, "Projects, Groups, Events and Users"
        
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
    if mode not in ['or_fail', 'direct', 'direct_html', 'threaded', 'override']:
        mode = 'or_fail'
    
    subject =  mode + ': Testmail from Housekeeping at %s' % str(now())
    template = 'cosinnus/common/internet_explorer_not_supported.html'
    retmsg = '\n\n<br><br> Use ?mode=[or_fail, direct, direct_html, threaded, override]\n\nThe Answer was: '
    
    if mode == 'or_fail':
        retmsg += force_text(send_mail_or_fail(request.user.email, subject, template, {}))
        return HttpResponse('Sent mail using or_fail mode. ' + retmsg)
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
