from django.urls import include, path
from rest_framework import routers

from cosinnus_event.calendar.api import CosinnusCalendarSyncedEventsViewSet, CosinnusCalendarViewSet

urlpatterns = []

router = routers.SimpleRouter()
router.register('events', CosinnusCalendarViewSet, 'calendar-event')
router.register('internal_events', CosinnusCalendarSyncedEventsViewSet, 'calendar-synced-event')
urlpatterns += [path('api/v3/spaces/<int:group_id>/calendar/', include(router.urls))]
