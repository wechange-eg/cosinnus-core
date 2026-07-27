from django.urls import include, path
from rest_framework import routers

from cosinnus_marketplace.api_frontend.views import CosinnusOfferViewSet

urlpatterns = []

router = routers.SimpleRouter()
router.register('offers', CosinnusOfferViewSet, 'personal-offer')
urlpatterns += [path('api/v3/', include(router.urls))]
