from django.http.response import JsonResponse
from rest_framework import viewsets
from rest_framework.views import APIView

from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.models.tagged import BaseTagObject
from .serializers import CosinnusSocietySerializer, CosinnusProjectSerializer, OrganisationListSerializer, \
    OrganisationRetrieveSerializer


class PublicCosinnusGroupFilterMixin(object):

    def get_queryset(self):
        queryset = self.queryset
        # filter for current portal
        queryset = queryset.filter(portal=CosinnusPortal.get_current())
        # Filter visibility
        queryset = queryset.filter(is_active=True)
        return queryset


class PublicTaggableObjectFilterMixin(object):

    def get_queryset(self):
        queryset = self.queryset
        # filter for current portal
        queryset = queryset.filter(group__portal=CosinnusPortal.get_current())
        # Filter visibility
        queryset = queryset.filter(group__is_active=True, media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        return queryset


class CosinnusSocietyViewSet(PublicCosinnusGroupFilterMixin,
                             viewsets.ReadOnlyModelViewSet):
    queryset = CosinnusSociety.objects.all()
    serializer_class = CosinnusSocietySerializer

    def get_queryset(self):
        """
        Optionally filter by group
        FIXME: Use generic filters here after upgrade to django-filter==0.15.0
        """
        queryset = super().get_queryset()
        # Order
        query_params = self.request.query_params.copy()
        order_by = query_params.pop('order_by', ['-created',])
        queryset = queryset.order_by(*order_by)
        # Overwrite ugly but commonly used filters
        FILTER_MAP = {
            'tags': 'media_tag__tags__name'
        }
        VALUE_MAP = {
            'false': False,
            'true': True
        }
        for key, value in list(query_params.items()):
            if key in (self.pagination_class.limit_query_param,
                       self.pagination_class.offset_query_param):
                continue
            key = FILTER_MAP.get(key, key)
            value = VALUE_MAP.get(value, value)
            if value is not None:
                if key.startswith('exclude_'):
                    queryset = queryset.exclude(**{key[8:]: value})
                else:
                    queryset = queryset.filter(**{key: value})
        return queryset


class CosinnusProjectViewSet(CosinnusSocietyViewSet):

    queryset = CosinnusProject.objects.all()
    serializer_class = CosinnusProjectSerializer


class OrganisationViewSet(PublicCosinnusGroupFilterMixin,
                          viewsets.ReadOnlyModelViewSet):

    queryset = CosinnusProject.objects.all()
    serializer_class = OrganisationListSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganisationListSerializer
        if self.action == 'retrieve':
            return OrganisationRetrieveSerializer
        return OrganisationRetrieveSerializer


class UserView(APIView):
    """
    Used by Oauth2 authentication (Rocket.Chat) to retrieve user details
    """

    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ""
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            return JsonResponse({
                'success': True,
                'id': str(user.id),
                'email': user.email,
                'name': user.get_full_name(),
                'avatar': avatar_url,
            })
        else:
            return JsonResponse({
                'success': False,
            })
