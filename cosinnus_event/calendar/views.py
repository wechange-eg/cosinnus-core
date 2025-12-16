import logging

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

from cosinnus.utils.permissions import check_ug_admin
from cosinnus.views.mixins.group import RequireReadMixin

logger = logging.getLogger(__name__)


class CalendarView(RequireReadMixin, TemplateView):
    """Main calendar app view containing a div used for the frontend app initialization."""

    template_name = 'cosinnus_event/calendar/calendar.html'

    def get(self, request, *args, **kwargs):
        if not self.group.nextcloud_calendar_url and check_ug_admin(request.user, self.group):
            # add admin warning
            message = _(
                'If the Calendar is not available withing a few minutes, some technical difficulties occurred with '
                'the calendar service. Try disabling and re-enabling the events app in the settings. '
                'If the problems persist, please contact the support. We apologize for the inconveniences!'
            )
            messages.warning(self.request, message)
        return super(CalendarView, self).get(request, *args, **kwargs)


calendar_view = CalendarView.as_view()
