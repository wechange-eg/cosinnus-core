from django.urls import include, path
from rest_framework import routers

from cosinnus_event.api_frontend.views import CosinnusEventViewSet, CosinnusPollViewSet

urlpatterns = []

router = routers.SimpleRouter()
router.register('events', CosinnusEventViewSet, 'personal-event')
router.register('polls', CosinnusPollViewSet, 'personal-poll')
urlpatterns += [path('api/v3/', include(router.urls))]
