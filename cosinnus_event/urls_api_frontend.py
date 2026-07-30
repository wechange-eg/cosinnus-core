from django.urls import include, path
from rest_framework import routers

from cosinnus_event.api_frontend.views import CosinnusEventPollViewSet, CosinnusEventViewSet

urlpatterns = []

router = routers.SimpleRouter()
router.register('events', CosinnusEventViewSet, 'personal-event')
router.register('event_polls', CosinnusEventPollViewSet, 'personal-event-poll')
urlpatterns += [path('api/v3/', include(router.urls))]
