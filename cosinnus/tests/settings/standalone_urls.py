from django.urls import include, path
from django.contrib import admin

from cosinnus.core.registries import url_registry

"""
Basic standalone url configuration that is used as ROOT_URLCONF in the standalone_settings allowing to initialize
cosinnus without a portal.
"""

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("djajax.urls", "djajax"), namespace="djajax")),
    path("", include(("cosinnus.urls", "cosinnus"), namespace="cosinnus")),
    path("", include((url_registry.api_urlpatterns, "cosinnus"), namespace="cosinnus-api")),
    path("select2/", include("django_select2.urls")),
    path("captcha/", include("captcha.urls")),
    path("", include("cosinnus.utils.django_auth_urls")),
    # leave at the end
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]
