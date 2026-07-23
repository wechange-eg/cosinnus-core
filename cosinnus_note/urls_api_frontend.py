from django.urls import include, path
from rest_framework import routers

from cosinnus_note.api_frontend.views import CosinnusNoteViewSet

urlpatterns = []

router = routers.SimpleRouter()
router.register('notes', CosinnusNoteViewSet, 'personal-note')
urlpatterns += [path('api/v3/', include(router.urls))]
