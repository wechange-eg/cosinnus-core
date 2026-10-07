from django.urls import include, path
from rest_framework import routers

from cosinnus.conf import settings
from cosinnus_event.api_frontend.views import CosinnusEventPollViewSet, CosinnusEventViewSet

urlpatterns = []

if 'cosinnus_event' not in settings.COSINNUS_DISABLED_COSINNUS_APPS:
    router = routers.SimpleRouter()
    router.register('events', CosinnusEventViewSet, 'event')
    router.register('event_polls', CosinnusEventPollViewSet, 'event-poll')
    urlpatterns += [path('api/v3/', include(router.urls))]
