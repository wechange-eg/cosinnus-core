from django_cron import Schedule

from cosinnus.cron import CosinnusCronJobBase
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_conference.utils import send_conference_reminder


class SendConferenceReminders(CosinnusCronJobBase):
    """
    Send conference reminder emails 1 week/day/hour before conference
    """

    RUN_EVERY_MINS = 10
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus_conference.send_conference_reminders'

    def do(self):
        field_names = ['week_before', 'day_before', 'hour_before']
        queryset = get_cosinnus_group_model().objects
        for field_name in field_names:
            for conference in queryset.to_be_reminded(field_name=field_name):
                send_conference_reminder(conference, field_name=field_name)
        return
