from django_cron import Schedule

from cosinnus.conf import settings            
from cosinnus.cron import CosinnusCronJobBase
from cosinnus_event.utils.bbb_streaming import trigger_streamer_status_changes


class TriggerBBBStreamers(CosinnusCronJobBase):
    """ Triggers creates/starts/stops/deletes for streamers for ConferenceEvents. """
    
    RUN_EVERY_MINS = 1 # every 1 min (or every time the cron runs at least)
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    
    cosinnus_code = 'cosinnus.trigger_bbb_streamers'
    
    def do(self):
        if settings.COSINNUS_CONFERENCES_ENABLED and settings.COSINNUS_CONFERENCES_STREAMING_ENABLED:
            trigger_streamer_status_changes()