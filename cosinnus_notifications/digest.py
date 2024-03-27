# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

import datetime
import logging

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import translation, timezone
from django.utils.html import strip_tags
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus_notifications.models import UserNotificationPreference,\
    NotificationEvent, UserMultiNotificationPreference
from cosinnus_notifications.notifications import NO_NOTIFICATIONS_ID,\
    ALL_NOTIFICATIONS_ID, NOTIFICATION_REASONS,\
    render_digest_item_for_notification_event,\
    get_multi_preference_notification_ids, is_notification_multipref,\
    get_superceded_multi_preferences, get_requires_object_state_check
from cosinnus.templatetags.cosinnus_tags import full_name, cosinnus_setting
from cosinnus.core.mail import send_mail_or_fail
from cosinnus.utils.permissions import check_object_read_access,\
    check_user_can_receive_emails
import traceback
from django.templatetags.static import static
from cosinnus.models.profile import GlobalUserNotificationSetting
from cosinnus.utils.functions import resolve_attributes
from cosinnus.utils.files import get_image_url_for_icon
from cosinnus.utils.user import is_user_active
import copy

logger = logging.getLogger('cosinnus')

# this category header will only be shown if there is at least one other category defined in
# COSINNUS_NOTIFICATIONS_DIGEST_CATEGORIES
DEFAULT_DIGEST_CATEGORY = [
    (_('Groups and Projects'), [], 'fa-sitemap', 'cosinnus:user-dashboard', None),
]


def send_digest_for_current_portal(digest_setting, debug_run_for_user=None, debug_force_show_all=False):
    """ Sends out a daily/weekly digest email to all users *IN THE CURRENT PORTAL*
             who have any notification preferences set to that frequency.
        We will send all events that happened within this
        
        Will not use an own thread because it is assumend that this is run from a management command.
        TODO: We may want to split up the user-loop into 4 independent threads covering 1/4th of the users each
              to balance loads better.
    
        @param digest_setting: UserNotificationPreference.SETTING_DAILY or UserNotificationPreference.SETTING_WEEKLY
        @param debug_run_for_user: if set to a User object, this will only generate a test digest for the given user
            and return it as html string. no portal modifications will be made
    """
    portal = CosinnusPortal.get_current()
    portal_group_ids = portal.groups.all().filter(is_active=True).values_list('id', flat=True)
    
    # read the time for the last sent digest of this time
    # (its saved as a string, but django QS will auto-box it when filtering on datetime fields)
    TIME_DIGEST_START = portal.saved_infos.get(CosinnusPortal.SAVED_INFO_LAST_DIGEST_SENT % digest_setting, None)
    if not TIME_DIGEST_START:
        TIME_DIGEST_START = now() - datetime.timedelta(days=UserNotificationPreference.SETTINGS_DAYS_DURATIONS[digest_setting])
    TIME_DIGEST_END = now()
    
    # the main Notification Events QS. anything not in here did not happen in the digest's time span
    timescope_notification_events = NotificationEvent.objects.filter(date__gte=TIME_DIGEST_START, date__lt=TIME_DIGEST_END)
    if debug_run_for_user:
        users = [debug_run_for_user]
    else:
        users = get_user_model().objects.all().filter(id__in=portal.members)
        extra_info = {
            'notification_event_count': timescope_notification_events.count(),
            'potential_user_count': users.count(), 
        }
        logger.info('Now starting to sending out digests of SETTING=%s in Portal "%s". Data in extra.' % \
                    (UserNotificationPreference.SETTING_CHOICES[digest_setting][1], portal.slug), extra=extra_info)
        if settings.DEBUG:
            print((">> ", extra_info))
    
    
    emailed = 0
    for user in users:
        if debug_run_for_user and debug_force_show_all:
            global_wanted = True
            multi_prefs = list(UserMultiNotificationPreference.objects.filter(user=user, portal=CosinnusPortal.get_current(), setting=digest_setting)\
                    .values_list('multi_notification_id', flat=True))
        else:
            if getattr(settings, 'COSINNUS_DIGEST_ONLY_FOR_ADMINS', False) and not user.is_superuser:
                continue
            if not check_user_can_receive_emails(user):
                continue
        
            # get all of user's multi prefs for this digest setting 
            only_multi_prefs_wanted = False
            multi_prefs = list(UserMultiNotificationPreference.objects.filter(user=user, portal=CosinnusPortal.get_current(), setting=digest_setting)\
                    .values_list('multi_notification_id', flat=True))
            # check global blanket settings
            global_wanted = False # flag to allow all events
            global_setting = GlobalUserNotificationSetting.objects.get_for_user(user)
            
            # check if global blanketing settings allow for sending this digest to the user
            if global_setting != digest_setting and global_setting != GlobalUserNotificationSetting.SETTING_GROUP_INDIVIDUAL:
                if not multi_prefs:
                    # users who don't have the global setting AND the multi pref setting set to this digest never get an email
                    continue 
                else:
                    # user still has a multi pref setting for this digest_setting, so go on and check
                    only_multi_prefs_wanted = True 
            
            if (digest_setting == UserNotificationPreference.SETTING_DAILY and global_setting == GlobalUserNotificationSetting.SETTING_DAILY) \
                    or (digest_setting == UserNotificationPreference.SETTING_WEEKLY and global_setting == GlobalUserNotificationSetting.SETTING_WEEKLY):
                global_wanted = True # user wants ALL events in his digest for this digest setting

        cur_time_zone = timezone.get_current_timezone()
        user_time_zone = user.cosinnus_profile.timezone.zone
        cur_language = translation.get_language()
        try:
            # only active users that have logged in before accepted the TOS get notifications
            if not user.is_active or not user.last_login or not user.cosinnus_profile.tos_accepted:
                continue
            
            # switch language to user's preference language so all i18n and date formats are in their language
            translation.activate(getattr(user.cosinnus_profile, 'language', settings.LANGUAGES[0][0]))

            # switch time zone to user's preference time zone so all time formats are in their time zones
            timezone.activate(user_time_zone)
            
            # get all notification events where the user is in the intended audience
            events = timescope_notification_events.filter(audience__contains=',%d,' % user.id)
            
            # if we have a blanket YES for this digest, filter events only by portal affiliance,
            # otherwise filter events by group notification settings
            if global_wanted:
                events = events.filter(group_id__in=portal_group_ids)
            elif only_multi_prefs_wanted:
                # set the regular group events to none; mix in multi pref events later
                events = NotificationEvent.objects.none()
            else:
                # these groups will never get digest notifications because they have a blanketing NONE setting or 
                # ALL setting (of anything but this ``digest_setting``)
                # (they may still have individual preferences in the DB, which are ignored because of the blanket setting)
                unwanted_digest_settings = [key for key in list(dict(UserNotificationPreference.SETTING_CHOICES).keys()) if key != digest_setting]
                exclude_digest_groups = UserNotificationPreference.objects.filter(user=user, group_id__in=portal_group_ids) 
                exclude_digest_groups = exclude_digest_groups.filter(Q(notification_id=ALL_NOTIFICATIONS_ID, setting__in=unwanted_digest_settings) | Q(notification_id=NO_NOTIFICATIONS_ID))
                exclude_digest_groups = exclude_digest_groups.values_list('group_id', flat=True)  
                
                # find out any notification preferences the user has for groups in this portal with the daily/weekly setting
                # if he doesn't have any, we will not send a mail for them
                prefs = UserNotificationPreference.objects.filter(user=user, group_id__in=portal_group_ids, setting=digest_setting)
                prefs = prefs.exclude(notification_id=NO_NOTIFICATIONS_ID).exclude(group_id__in=exclude_digest_groups)
                
                if len(prefs) == 0:
                    continue
                
                # only for these groups does the user get any digest news at all
                pref_group_ids = list(set([pref.group for pref in prefs]))
                # so filter for these groups
                events = events.filter(group_id__in=pref_group_ids)
                
            # add multi pref events that the user wants to see to regular events
            if multi_prefs:
                multi_pref_notification_ids = []
                for multi_pref in multi_prefs:
                    multi_pref_notification_ids.extend(get_multi_preference_notification_ids(multi_pref))
                # filter all notification events to fit multi prefs andbe in the current portal
                multi_pref_events = timescope_notification_events.filter(
                    notification_id__in=multi_pref_notification_ids,
                    group_id__in=portal_group_ids
                )
                events = events | multi_pref_events
                
            if events.count() == 0:
                continue
            
            if not global_wanted and not only_multi_prefs_wanted:
                # collect a comparable hash for all wanted user prefs
                wanted_group_notifications = ['%(group_id)d__%(notification_id)s' % {
                    'group_id': pref.group_id,
                    'notification_id': pref.notification_id,
                } for pref in prefs]
            
            # cluster event messages by categories and then by group. 
            # from here on, the user will almost definitely get an email.
            categories = copy.deepcopy(settings.COSINNUS_NOTIFICATIONS_DIGEST_CATEGORIES) or []
            categories += DEFAULT_DIGEST_CATEGORY
            body_html = ''
            categorized_notification_ids = [nid for __,nids,__,__,__ in categories for nid in nids]
            for cat_label, cat_notification_ids, cat_icon, cat_url_rev, cat_group_func in categories:
                # add category header if there is more than one category
                category_header_html = ''
                category_html = ''
                if len(categories) > 1:
                    header_context = {
                        'group_body_html': '', # empty on purpose as a header has no body
                        'group_image_url': portal.get_domain() + get_image_url_for_icon(cat_icon, large=True),
                        'group_url': reverse(cat_url_rev),
                        'group_name': cat_label,
                    }
                    category_header_html = render_to_string('cosinnus/html_mail/summary_group.html', context=header_context)
                
                for group in list(set(events.values_list('group', flat=True))): 
                    group_events = events.filter(group=group).order_by('-id') # id faster than ordering by created date 
                    
                    # filter only those events that the user actually has in his prefs, for this group and also
                    # check for target object existing, being visible to user, and other sanity checks if the user should see this object
                    wanted_group_events = []
                    for event in group_events:
                        # include the event only if it belongs to the right category,
                        # i.e. it is either in the current list of category-ids or 
                        # the current list is empty ("all ids") and the id does not 
                        # appear in any other category
                        _app_label, current_notification_id = event.notification_id.split('__')
                        if not (current_notification_id in cat_notification_ids or \
                                (len(cat_notification_ids) == 0 and current_notification_id not in categorized_notification_ids)):
                            continue
                        if cat_group_func is not None and hasattr(event, 'group') and event.group and not cat_group_func(event.group):
                            continue
                        
                        is_multipref = is_notification_multipref(event.notification_id)
                        statecheck = get_requires_object_state_check(event.notification_id)
                        if user == event.user:
                            continue  # users don't receive infos about events they caused
                        if not is_user_active(event.user):
                            continue # users who are inactive by now are probably banned, so ignore their content
                        if not is_multipref and not global_wanted and not only_multi_prefs_wanted: # skip finegrained preference check on blanket YES
                            if not (('%d__%s' % (event.group_id, ALL_NOTIFICATIONS_ID) in wanted_group_notifications) or \
                                    ('%d__%s' % (event.group_id, event.notification_id) in wanted_group_notifications)):
                                continue  # must have an actual subscription to that event type
                        if event.target_object is None:
                            continue  # referenced object has been deleted by now
                        if not check_object_read_access(event.target_object, user):
                            continue  # user must be able to even see referenced object 
                        # statecheck if defined, for example for checking if the user is still following the object
                        if statecheck:
                            if not resolve_attributes(event.target_object, statecheck, func_args=[user]):
                                continue
                        wanted_group_events.append(event)
                    
                    wanted_group_events = sorted(wanted_group_events,  key=lambda e: e.date)
                    
                    # Throw out duplicate events (eg "X was updated" multiple times) for the same object and superceded events. 
                    # The most recent event is always kept.
                    # - follow-events have a supercede list of events that are always less important than the follow-event
                    # - this means that a "created" event would be thrown out by a later "an item you followed was updated" on the same object
                    for this_event in wanted_group_events[:]:
                        for other_event in wanted_group_events[:]:
                            if not other_event == this_event:
                                unprefixed_this_notification_id = this_event.notification_id.split('__')[1]
                                if this_event.target_object == other_event.target_object and \
                                        (this_event.notification_id == other_event.notification_id or \
                                         unprefixed_this_notification_id in get_superceded_multi_preferences(other_event.notification_id)):
                                    wanted_group_events.remove(this_event)
                                    break
                    
                    if wanted_group_events:
                        group = wanted_group_events[0].group # needs to be resolved, values_list returns only id ints
                        group_body_html = '\n'.join([render_digest_item_for_notification_event(event) for event in wanted_group_events])
                        # categories may display their items in a condensed list directly under their header
                        # and the default category displays in a clustered form within a header for each group
                        # note: currently disabled and not extracted into a conf setting until it is wished for
                        condense_categories = False
                        if condense_categories and len(cat_notification_ids) > 0:
                            category_html += group_body_html + '\n'
                        else:
                            group_template_context = {
                                'group_body_html': mark_safe(group_body_html),
                                'group_image_url': CosinnusPortal.get_current().get_domain() + group.get_avatar_thumbnail_url(),
                                'group_url': group.get_absolute_url(),
                                'group_name': group['name'],
                            }
                            group_html = render_to_string('cosinnus/html_mail/summary_group.html', context=group_template_context)
                            category_html += group_html + '\n'
                # end for group
                
                if category_html:
                    category_html = category_header_html + '\n' + category_html
                    body_html += category_html + '\n'
                    # we currently don't have a proper category header, so add a larger space in-between categories, except for the last
                    if len(cat_notification_ids) > 0:
                        body_html += '<br/><br/>\n'
            # end for category
                    
                    
            
            if debug_run_for_user:
                return body_html
            # send actual email with full frame template
            if body_html:
                _send_digest_email(user, mark_safe(body_html), TIME_DIGEST_END, digest_setting)
                emailed += 1
            
        except Exception as e:
            # we never want this subroutine to just die, we need the final saves at the end to ensure
            # the same items do not get into digests twice
            logger.error('An error occured while doing a digest for a user! Exception was: %s' % force_str(e), 
                         extra={'exception': e, 'trace': traceback.format_exc(), 'user_mail': user.email, 'digest_setting': digest_setting})
            if settings.DEBUG:
                raise
        finally:
            # switch language back
            translation.activate(cur_language)
            timezone.activate(cur_time_zone)
    
    # if we do a debug run and the user had no notifications to show, return empty HTML
    if debug_run_for_user:
        return ''
            
    # save the end time of the digest period as last digest time for this type
    portal.saved_infos[CosinnusPortal.SAVED_INFO_LAST_DIGEST_SENT % digest_setting] = TIME_DIGEST_END
    portal.save()
    
    deleted = cleanup_stale_notifications()
    
    extra_log = {
        'users_emailed': emailed,
        'total_users': len(users),
        'deleted_stale_notifications': deleted,
        'remaining_past_and_future_notifications': NotificationEvent.objects.all().count(),
    }
    logger.info('Finished sending out digests of SETTING=%s in Portal "%s". Data in extra.' % (UserNotificationPreference.SETTING_CHOICES[digest_setting][1], portal.slug), extra=extra_log)
    if settings.DEBUG:
        print(extra_log)


def _get_digest_email_context(receiver, body_html, digest_generation_time, digest_setting):
    """ Gets the context for rendering the template for the actual digest mail.
        Used for `_send_digest_email()` """
    portal_name =  _(settings.COSINNUS_BASE_PAGE_TITLE_TRANS)
    if digest_setting == UserNotificationPreference.SETTING_DAILY:
        subject = _('Your daily digest for %(portal_name)s') % {'portal_name': portal_name}
        topic = _('This is what happened during the last day!')
        reason = NOTIFICATION_REASONS['daily_digest']
    else:
        subject = _('Your weekly digest for %(portal_name)s') % {'portal_name': portal_name}
        topic = _('This is what happened during the last week!')
        reason = NOTIFICATION_REASONS['weekly_digest']
    portal = CosinnusPortal.get_current()
    site = portal.site
    domain = portal.get_domain()
    preference_url = '%s%s' % (domain, reverse('cosinnus:notifications'))
    portal_image_url = '%s%s' % (domain, static('img/email-header.png'))
    
    context = {
        'site': site,
        'site_name': site.name,
        'domain_url': domain,
        'portal_url': domain,
        'portal_image_url': portal_image_url,
        'portal_name': portal_name,
        'receiver': receiver, 
        'addressee': mark_safe(strip_tags(receiver.first_name)), 
        'topic': topic,
        'digest_body_html': mark_safe(body_html),
        'prefs_url': mark_safe(preference_url),
        'notification_reason': reason,
        'digest_setting': digest_setting,
        'subject': subject,
    }
    return context


def _send_digest_email(receiver, body_html, digest_generation_time, digest_setting):
    """ Prepares the actual digest mail and sends it """
    template = '/cosinnus/html_mail/digest.html'
    context = _get_digest_email_context(receiver, body_html, digest_generation_time, digest_setting)
    send_mail_or_fail(receiver.email, context['subject'], template, context, is_html=True)


def cleanup_stale_notifications():
    """ Deletes all notification events that will never be used again to compose a digest. 
    
        This deletes all notification events that have been created more than 3x the length 
        of the longest digest period ago. I.e. if our longest digest is 1 week, this will delete
        all items older than 21 days. This is a naive safety measure to prevent multiple digests
        running at the same time to delete each other's notification events from under them.
        
        @return the count of the items deleted """
        
    max_days = max(dict(UserNotificationPreference.SETTINGS_DAYS_DURATIONS).values())
    time_digest_stale = now() - datetime.timedelta(days=(1+max_days*2))
    stale_notification_events = NotificationEvent.objects.filter(date__lt=time_digest_stale)
    
    deleted = stale_notification_events.count()
    stale_notification_events.delete()
    return deleted
