from django.urls import include, path
from rest_framework import routers

from cosinnus.conf import settings
from cosinnus_poll.api_frontend.views import CosinnusPollViewSet

urlpatterns = []

if 'cosinnus_poll' not in settings.COSINNUS_DISABLED_COSINNUS_APPS:
    router = routers.SimpleRouter()
    router.register('polls', CosinnusPollViewSet, 'poll')
    urlpatterns += [path('api/v3/', include(router.urls))]
