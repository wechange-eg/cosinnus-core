import logging

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

from cosinnus.conf import settings
from cosinnus.utils.permissions import check_ug_admin, check_ug_membership
from cosinnus.views.mixins.group import DipatchGroupURLMixin
from cosinnus_cloud.hooks import get_nc_user_id, group_cloud_app_activated_sub
from cosinnus_event.calendar.integration import CosinnusCalendarIntegrationHandler

logger = logging.getLogger(__name__)


class CosinnusCalendarView(DipatchGroupURLMixin, TemplateView):
    """
    Main calendar app view containing a div used for the frontend app initialization.
    If the group does not have a NextCloud calendar the creation hooks are triggered here.
    """

    template_name = 'cosinnus_event/calendar/calendar.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and not self.group.nextcloud_calendar_url:
            # initialize Nextcloud calendar
            if not self.group.nextcloud_group_id:
                # initialize cloud integration including calendar
                group_cloud_app_activated_sub(sender=None, group=self.group, apps=['cosinnus_event'])
            else:
                # initialize calendar via integration handler
                integration_handler = CosinnusCalendarIntegrationHandler()
                integration_handler.do_group_nextcloud_group_initialized(sender=None, group=self.group)

            if check_ug_admin(request.user, self.group):
                # add admin warning
                message = _(
                    'If the Calendar is not available withing a few minutes, some technical difficulties occurred with '
                    'the calendar service. If the problems persist, please contact the support. We apologize for the '
                    'inconveniences!'
                )
                messages.warning(self.request, message)
        return super(CosinnusCalendarView, self).get(request, *args, **kwargs)

    def get_user_calendar_url(self, user, user_is_group_member):
        """Convert the admin CalDAV URL to a user CalDAV URL, as NextCloud uses user specific CalDAV URLs."""
        user_calendar_url = ''
        if user_is_group_member and self.group.nextcloud_calendar_url:
            user_calendar_url = self.group.nextcloud_calendar_url.replace(
                f'/{settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME}/',
                f'/{get_nc_user_id(self.request.user)}/',
            )
            user_calendar_url = user_calendar_url[:-1]
            user_calendar_url += f'_shared_by_{settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME}/'
            return user_calendar_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        user = self.request.user
        user_is_group_member = check_ug_admin(user, self.group) or check_ug_membership(user, self.group)
        context.update(
            {
                'private_events_available': user_is_group_member,
                'user_calendar_url': self.get_user_calendar_url(user, user_is_group_member),
            }
        )
        return context


calendar_view = CosinnusCalendarView.as_view()
