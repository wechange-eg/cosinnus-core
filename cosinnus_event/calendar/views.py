import logging

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

from cosinnus.utils.permissions import check_ug_admin, check_ug_membership
from cosinnus.views.mixins.group import DipatchGroupURLMixin

logger = logging.getLogger(__name__)


class CalendarView(DipatchGroupURLMixin, TemplateView):
    """Main calendar app view containing a div used for the frontend app initialization."""

    template_name = 'cosinnus_event/calendar/calendar.html'

    def get(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and not self.group.nextcloud_calendar_url
            and check_ug_admin(request.user, self.group)
        ):
            # add admin warning
            message = _(
                'If the Calendar is not available withing a few minutes, some technical difficulties occurred with '
                'the calendar service. Try disabling and re-enabling the events app in the settings. '
                'If the problems persist, please contact the support. We apologize for the inconveniences!'
            )
            messages.warning(self.request, message)
        return super(CalendarView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        user = self.request.user
        user_is_group_member = check_ug_admin(user, self.group) or check_ug_membership(user, self.group)
        context.update(
            {
                'private_events_available': user_is_group_member,
            }
        )
        return context


calendar_view = CalendarView.as_view()
