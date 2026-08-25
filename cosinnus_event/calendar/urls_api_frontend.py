from django.urls import include, path
from rest_framework import routers

from cosinnus_event.calendar.api import (
    CalendarRepairMembershipView,
    CosinnusCalendarSyncedEventsViewSet,
    CosinnusCalendarViewSet,
)

urlpatterns = []

router = routers.SimpleRouter()
router.register('events', CosinnusCalendarViewSet, 'calendar-event')
router.register('internal_events', CosinnusCalendarSyncedEventsViewSet, 'calendar-synced-event')
urlpatterns += [
    path('api/v3/spaces/<int:group_id>/calendar/', include(router.urls)),
    path(
        'api/v3/spaces/<int:group_id>/calendar/repair_membership/',
        CalendarRepairMembershipView.as_view(),
        name='calendar-repair-membership',
    ),
]
