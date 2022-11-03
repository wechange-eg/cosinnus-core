# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_text
from django.utils.timezone import now
from django_cron import CronJobBase, Schedule

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.profile import get_user_profile_model
from cosinnus.views.profile import delete_userprofile
from cosinnus_conference.utils import update_conference_premium_status
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_event.models import Event


logger = logging.getLogger('cosinnus')


class CosinnusCronJobBase(CronJobBase):
    
    cosinnus_code = None
        
    @property
    def code(self):
        """ Unique cron id, must contain CosinnusPortal slug, or different portal crons will overlap """
        if not self.cosinnus_code:
            raise ImproperlyConfigured('Must define a ``cosinnus_code`` property for your cron object!')
        return 'p_%s_%s' % (CosinnusPortal.get_current().slug, self.cosinnus_code)
    
    def __init__(self, *args, **kwargs):
        super(CosinnusCronJobBase, self).__init__(*args, **kwargs)
        initialize_cosinnus_after_startup()
    
    def do(self):
        raise ImproperlyConfigured('``do()`` must be overridden in your cron object!')


class DeleteScheduledUserProfiles(CosinnusCronJobBase):
    """ Triggers a profile delete on all user profiles whose `scheduled_for_deletion_at`
        datetime is in the past. """
    
    RUN_EVERY_MINS = 60 # every 1 hour
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    
    cosinnus_code = 'cosinnus.delete_scheduled_user_profiles'
    
    def do(self):
        profiles_to_delete = get_user_profile_model().objects\
            .exclude(scheduled_for_deletion_at__exact=None)\
            .filter(scheduled_for_deletion_at__lte=now())
        
        for profile in profiles_to_delete:
            try:
                # sanity checks are done within this function, no need to do any here
                user_id = profile.user.id
                delete_userprofile(profile.user)
                logger.info('delete_userprofile() cronjob: profile was deleted completely after 30 days', extra={'user_id': user_id})
            except Exception as e:
                logger.error('delete_userprofile() cronjob: threw an exception during the DeleteScheduledUserProfiles cronjob! (in extra)', extra={'exception': force_text(e)})
            

class UpdateConferencePremiumStatus(CosinnusCronJobBase):
    """ Updates the premium status for all conferences. """
    
    RUN_EVERY_MINS = 1 # every 1 min (or every time the cron runs at least)
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    
    cosinnus_code = 'cosinnus.update_conference_premium_status'
    
    def do(self):
        if settings.COSINNUS_CONFERENCES_ENABLED:
            update_conference_premium_status()


class SwitchGroupPremiumFeatures(CosinnusCronJobBase):
    """ Switches premium group features off for groups whose premium time signified by
        `enable_user_premium_choices_until` has expired. Will set 
        `enable_user_premium_choices_until` to empty afterwards and add a key
        'premium_features_expired_on' with the current date to the group['settings'].
        Will only run if relevant premium features for groups are enabled on this portal. """
    
    RUN_EVERY_MINS = 60 # every 1 hour
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    
    cosinnus_code = 'cosinnus.switch_group_premium_features'
    
    def do(self):
        # currently the only setting that signifies premium features for groups.
        # may need to add a better check in the future if more are to come
        if settings.COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED:
            portal_groups = get_cosinnus_group_model().objects.all_in_portal()
            today = now().date()
            groups_to_expire = portal_groups.filter(enable_user_premium_choices_until__lt=today)
            
            count = 0
            for group in groups_to_expire:
                group_events = Event.objects.filter(group=group)
                objects_to_reset = [group] + list(group_events)
                # reset video conferences for group and all of its events                
                for obj in objects_to_reset:
                    # reset bbb viceo conference setting if set (fallback to fairmeeting server if active)
                    if obj.video_conference_type == obj.BBB_MEETING:
                        if CosinnusPortal.get_current().video_conference_server:
                            obj.video_conference_type = obj.FAIRMEETING
                        else:
                            obj.video_conference_type = obj.NO_VIDEO_CONFERENCE
                        obj.save()
                # reset `enable_user_premium_choices_until` field
                group.enable_user_premium_choices_until = None
                # add marker field for expired premium features
                group.settings['premium_features_expired_on'] = today
                group.save()
                count += 1
            return f'Expired {count} premium groups.'
        return 'Never ran, premium features are not enabled.'
