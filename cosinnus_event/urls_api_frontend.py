from django.urls import include, path
from rest_framework import routers

from cosinnus_event.api_frontend.views import CosinnusPollViewSet

urlpatterns = []

router = routers.SimpleRouter()
router.register('polls', CosinnusPollViewSet, 'personal-poll')
urlpatterns += [path('api/v3/', include(router.urls))]
