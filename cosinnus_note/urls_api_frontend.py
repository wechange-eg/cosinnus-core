from django.urls import include, path
from rest_framework import routers

from cosinnus.conf import settings
from cosinnus_note.api_frontend.views import CosinnusNoteViewSet

urlpatterns = []

if 'cosinnus_note' not in settings.COSINNUS_DISABLED_COSINNUS_APPS:
    router = routers.SimpleRouter()
    router.register('notes', CosinnusNoteViewSet, 'note')
    urlpatterns += [path('api/v3/', include(router.urls))]
