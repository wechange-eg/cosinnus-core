from datetime import timedelta
import logging

from django.utils.crypto import get_random_string
from django.utils.timezone import now

from cosinnus.conf import settings
from cosinnus_conference.bbb_streaming import create_streamer, delete_streamer, \
    start_streamer, stop_streamer


logger = logging.getLogger('cosinnus')

# key for the streamer id in `event.settings`
SETTINGS_STREAMER_ID = 'streaming_streamer_id'
# key for if the streamer is currently running in `event.settings`
SETTINGS_STREAMER_RUNNING = 'streaming_streamer_running'


def create_streamer_for_event(event):
    """ Creates a streamer using the BBB streaming API for this event. This does
        not start the actual stream yet.
        Only executes if there is not already a streamer ID set. """
    
    from cosinnus.apis.bigbluebutton import BigBlueButtonAPI
    if event.settings.get(SETTINGS_STREAMER_ID, None):
        logger.warn('BBB Streaming: Could not create a streamer because one was already created!', extra={
            'event_id': event.id,
            'streamer_id': event.settings.get(SETTINGS_STREAMER_ID),
        })
        return
    if not event.enable_streaming or not event.stream_url or not event.stream_key:
        logger.error('BBB Streaming: Could not create a streamer for event because streaming was not enabled for it or stream url or key was missing!', extra={
            'event_id': event.id,
        })
        return
    if not event.media_tag.bbb_room:
        success = event.check_and_create_bbb_room()
        if not success:
            logger.error('BBB Streaming: Could not create a streamer for event because no BBBRoom exists for it!', extra={
                'event_id': event.id,
            })
            return
    bbb_room = event.media_tag.bbb_room
    stream_url = event.stream_url.strip()
    if not stream_url.endswith('/'):
        stream_url += '/'
    stream_url += event.stream_key
    bbb_api_obj = BigBlueButtonAPI(source_object=event)

    streamer_uuid_name = f'Streamer-{event.group.portal.slug}-{event.id}-{get_random_string(8)}'
    streamer_id = create_streamer(
        name=streamer_uuid_name,
        bbb_url=bbb_api_obj.api_auth_url,
        bbb_secret=bbb_api_obj.api_auth_secret,
        meeting_id=bbb_room.meeting_id,
        stream_url=stream_url
    )
    if streamer_id is not None:
        event.settings[SETTINGS_STREAMER_ID] = streamer_id
        type(event).objects.filter(pk=event.pk).update(settings=event.settings)


def start_streamer_for_event(event):
    """ Starts the streaming for a previously created streamer (using `create_streamer_for_event`)
        for the BBB streaming API for this event.
        Only executes if there is a streamer ID set but the streamer is not yet running. """
        
    if not event.settings.get(SETTINGS_STREAMER_ID, None):
        logger.warn('BBB Streaming: Could not start a streamer because no streamer id existed!', extra={
            'event_id': event.id,
        })
        return 
    if event.settings.get(SETTINGS_STREAMER_RUNNING, False):
        logger.warn('BBB Streaming: Could not start a streamer because it was already running!', extra={
            'event_id': event.id,
        })
        return
    event.check_and_create_bbb_room()
    ret = start_streamer(event.settings.get(SETTINGS_STREAMER_ID))
    if ret is True:
        event.settings[SETTINGS_STREAMER_RUNNING] = True
        type(event).objects.filter(pk=event.pk).update(settings=event.settings)


def stop_streamer_for_event(event):
    """ Stops the streaming for a previously started streamer for the BBB streaming API for this event.
        Only executes if there is a streamer ID set and the streamer is running. """
    if not event.settings.get(SETTINGS_STREAMER_ID, None):
        logger.warn('BBB Streaming: Could not stop a streamer because no streamer id existed!', extra={
            'event_id': event.id,
        })
        return 
    if not event.settings.get(SETTINGS_STREAMER_RUNNING, False):
        logger.warn('BBB Streaming: Could not stop a streamer because it was not running!', extra={
            'event_id': event.id,
        })
        return 
    ret = stop_streamer(event.settings.get(SETTINGS_STREAMER_ID))
    if ret is True:
        if SETTINGS_STREAMER_RUNNING in event.settings:
            del event.settings[SETTINGS_STREAMER_RUNNING]
            type(event).objects.filter(pk=event.pk).update(settings=event.settings)


def delete_streamer_for_event(event):
    """ Deletes a previously created streamer for the BBB streaming API for this event.
        Only executes if there is a streamer ID set. """
    if not event.settings.get(SETTINGS_STREAMER_ID, None):
        logger.warn('BBB Streaming: Could not delete a streamer because no streamer id existed!', extra={
            'event_id': event.id,
        })
        return 
    delete_streamer(event.settings.get(SETTINGS_STREAMER_ID))
    # the return value only telss us that the streamer was deleted successfully. we also delete it from the event if
    # it returns False, because then the streamer was already deleted.
    # all other results produce an Exception anyways
    if SETTINGS_STREAMER_ID in event.settings:
        del event.settings[SETTINGS_STREAMER_ID]
        type(event).objects.filter(pk=event.pk).update(settings=event.settings)


def trigger_streamer_status_changes(events=None):
    """ Checks all streaming-enabled conference events whether any of their streamers should
        be created/started/stopped/deleted depending on the current point in time and 
        their streaming status.
        @param events: if supplied with a list of events, only checks those events, instead of
        all events in this portal """
    if not settings.COSINNUS_CONFERENCES_STREAMING_ENABLED or not settings.COSINNUS_PREMIUM_CONFERENCES_ENABLED:
        return
    
    if events is None:
        from cosinnus_event.models import ConferenceEvent
        events = ConferenceEvent.objects.filter(enable_streaming=True)
    
    for event in events:
        # events like coffee tables, without a start and end date, cannot be streamed
        if not event.from_date or not event.to_date:
            continue
        
        create_time = event.from_date - timedelta(minutes=settings.COSINNUS_CONFERENCES_STREAMING_API_CREATE_STREAMER_BEFORE_MINUTES)
        start_time = event.from_date - timedelta(minutes=settings.COSINNUS_CONFERENCES_STREAMING_API_START_STREAMER_BEFORE_MINUTES)
        stop_delete_time = event.to_date + timedelta(minutes=settings.COSINNUS_CONFERENCES_STREAMING_API_STOP_DELETE_STREAMER_AFTER_MINUTES)
        
        # creating and starting a streamer only works for conferences that are premium at this time
        # (stopping and deleting works regardless for sanity)
        if event.streaming_allowed:
            # check if we should create a streamer
            if event.enable_streaming and not event.settings.get(SETTINGS_STREAMER_ID, None) and \
                    create_time <= now() <= stop_delete_time:
                try:
                    create_streamer_for_event(event)
                except Exception as e:
                    logger.error('Event-Streaming: create_streamer trigger failed for event!', extra={
                        'event_id': event.id, 'exception': e})
            
            # check if we should start the streamer, if there is one
            if event.enable_streaming and event.settings.get(SETTINGS_STREAMER_ID, None) and \
                    not event.settings.get(SETTINGS_STREAMER_RUNNING, None) and \
                    start_time <= now() <= stop_delete_time:
                try:
                    start_streamer_for_event(event)
                except Exception as e:
                    logger.error('Event-Streaming: start_streamer trigger failed for event!', extra={
                        'event_id': event.id, 'exception': e})
        
        # events which have streamer settings still will be stopped/deleted *even if* their `enable_streaming`
        # is set to false, so we can stop streams that have just had their streaming disabled but are still running
        if event.settings.get(SETTINGS_STREAMER_RUNNING, None) and \
                event.settings.get(SETTINGS_STREAMER_ID, None) and \
                (event.enable_streaming == False or not event.streaming_allowed or stop_delete_time <= now() or now() <= start_time):
            try:
                stop_streamer_for_event(event)
            except Exception as e:
                logger.error('Event-Streaming: stop_streamer trigger failed for event!', extra={
                    'event_id': event.id, 'exception': e})
            
        # events which have streamer settings still will be stopped/deleted *even if* their `enable_streaming`
        # is set to false, so we can stop streams that have just had their streaming disabled but were still running
        if event.settings.get(SETTINGS_STREAMER_ID, None) and \
                (event.enable_streaming == False or not event.streaming_allowed or stop_delete_time <= now() or now() <= create_time):
            try:
                delete_streamer_for_event(event)
            except Exception as e:
                logger.error('Event-Streaming: delete_streamer trigger failed for event!', extra={
                    'event_id': event.id, 'exception': e})
            
