import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

from cosinnus.conf import settings
from cosinnus.models import BaseTagObject
from cosinnus.utils.permissions import check_ug_admin, check_ug_membership
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.mixins.group import DipatchGroupURLMixin, RequireWriteMixin
from cosinnus_cloud.hooks import get_nc_user_id, group_cloud_app_activated_sub
from cosinnus_event.calendar.integration import CosinnusCalendarIntegrationHandler

logger = logging.getLogger(__name__)


class CalendarRedirectMixin:
    """
    Mixin to redirect deprecated v2 event view to the v3 calendar.
    Note: The redirect can be bypassed using the forcev2 parameter to still access the v2 event pages.
    """

    # Extra setting to disble the redirect in a view. Used to disable the redirect in the poll views.
    v3_calendar_redirect_disabled = False

    def dispatch(self, request, *args, **kwargs):
        if (
            settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED
            and not self.v3_calendar_redirect_disabled
            and not request.GET.get('forcev2')
        ):
            v3_calendar_url = group_aware_reverse('cosinnus:event:calendar', kwargs={'group': self.group})
            if hasattr(self, 'object') and self.object.media_tag.visibility == BaseTagObject.VISIBILITY_ALL:
                # open event in v3 calendar
                v3_calendar_url += f'#public-{self.group.pk}-{self.object.pk}'
            return redirect(v3_calendar_url)
        return super(CalendarRedirectMixin, self).dispatch(request, *args, **kwargs)


class CosinnusCalendarView(DipatchGroupURLMixin, TemplateView):
    """
    Main calendar app view containing a div used for the frontend app initialization.
    If the group does not have a NextCloud calendar the creation hooks are triggered here.
    """

    template_name = 'cosinnus_event/calendar/calendar.html'

    def get(self, request, *args, **kwargs):
        if request.GET.get('forcev2'):
            # allow access to v2 calendar
            return redirect(group_aware_reverse('cosinnus:event:list', kwargs={'group': self.group}))
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


class CosinnusCalendarMigrateView(RequireWriteMixin, TemplateView):
    """Allows users to migrate private events to the NextCloud group calendar."""

    template_name = 'cosinnus_event/calendar/migrate.html'

    USER_SETTING_MIGRATION_DISMISSED = 'calendar_migration_dismissed'

    def post(self, request, *args, **kwargs):
        if 'start' in request.POST:
            # start the migration
            if self.group.calendar_migration_allowed():
                # start the migration task
                self.group.calendar_migration_set_status(self.group.CALENDAR_MIGRATION_STATUS_STARTED)
                try:
                    from cosinnus_event.calendar.integration import CALENDAR_SINGLETON

                    CALENDAR_SINGLETON.do_group_migrate_private_events(self.group)
                except Exception as e:
                    self.group.calendar_migration_set_status(self.group.CALENDAR_MIGRATION_STATUS_FAILED)
                    logger.exception(e)
        elif 'dismiss' in request.POST:
            # dismiss the migration for the user
            profile = request.user.cosinnus_profile
            profile.settings[self.USER_SETTING_MIGRATION_DISMISSED] = True
            profile.save(update_fields=['settings'])

            # redirect to calendar
            return redirect(group_aware_reverse('cosinnus:event:calendar', kwargs={'group': self.group}))
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CosinnusCalendarMigrateView, self).get_context_data(**kwargs)
        context.update(
            {
                'migration_required': self.group.calendar_migration_required(),
                'migration_allowed': self.group.calendar_migration_allowed(),
                'migration_status': self.group.calendar_migration_status(),
            }
        )
        return context


calendar_migrate_view = CosinnusCalendarMigrateView.as_view()
