from django.urls import include, path
from rest_framework import routers

from cosinnus.conf import settings
from cosinnus_marketplace.api_frontend.views import CosinnusOfferViewSet

urlpatterns = []

if 'cosinnus_marketplace' not in settings.COSINNUS_DISABLED_COSINNUS_APPS:
    router = routers.SimpleRouter()
    router.register('offers', CosinnusOfferViewSet, 'offer')
    urlpatterns += [path('api/v3/', include(router.urls))]
