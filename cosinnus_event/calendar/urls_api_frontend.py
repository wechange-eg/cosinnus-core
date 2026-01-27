from django.urls import include, path
from rest_framework import routers

from cosinnus_event.calendar.api import CalendarPublicEventViewSet

urlpatterns = []

router = routers.SimpleRouter()
router.register('events', CalendarPublicEventViewSet, 'calendar-event')
urlpatterns += [path('api/v3/group/<int:group_id>/calendar/', include(router.urls))]
