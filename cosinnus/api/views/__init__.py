import json

from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from oauth2_provider.decorators import protected_resource

from cosinnus.utils.user import filter_active_users
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.models.tagged import BaseTagObject
from ..serializers.group import CosinnusSocietySerializer, CosinnusProjectSerializer
from ..serializers.organisation import OrganisationListSerializer, OrganisationRetrieveSerializer
from ..serializers.user import UserSerializer


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


class CosinnusFilterQuerySetMixin:
    FILTER_CONDITION_MAP = {
    }
    FILTER_KEY_MAP = {
        'tags': 'media_tag__tags__name'
    }
    FILTER_VALUE_MAP = {
        'false': False,
        'true': True
    }
    FILTER_DEFAULT_ORDER = ['-created', ]

    def get_queryset(self):
        """
        Optionally filter by group
        FIXME: Use generic filters here after upgrade to django-filter==0.15.0
        """
        queryset = super().get_queryset()
        # Order
        query_params = self.request.query_params.copy()
        order_by = query_params.pop('order_by', self.FILTER_DEFAULT_ORDER)
        queryset = queryset.order_by(*order_by)
        # Overwrite ugly but commonly used filters
        for key, value in list(query_params.items()):
            if key in (self.pagination_class.limit_query_param,
                       self.pagination_class.offset_query_param):
                continue
            if key in self.FILTER_CONDITION_MAP:
                VALUE_MAP = self.FILTER_CONDITION_MAP.get(key)
                if value in VALUE_MAP:
                    (key, value), *rest = VALUE_MAP.get(value).items()
            key = self.FILTER_KEY_MAP.get(key, key)
            value = self.FILTER_VALUE_MAP.get(value, value)
            if value is not None:
                if key.startswith('exclude_'):
                    queryset = queryset.exclude(**{key[8:]: value})
                else:
                    queryset = queryset.filter(**{key: value})
        return queryset


class CosinnusSocietyViewSet(CosinnusFilterQuerySetMixin,
                             PublicCosinnusGroupFilterMixin,
                             viewsets.ReadOnlyModelViewSet):
    queryset = CosinnusSociety.objects.all()
    serializer_class = CosinnusSocietySerializer


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


class OAuthUserView(APIView):
    """
    Used by Oauth2 authentication (Rocket.Chat) to retrieve user details
    """

    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ""
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            return Response({
                'success': True,
                'id': user.username if user.username.isdigit() else str(user.id),
                'email': user.email.lower(),
                'name': user.get_full_name(),
                'avatar': avatar_url,
            })
        else:
            return Response({
                'success': False,
            })


@protected_resource(scopes=['read'])
def oauth_user(request):
    return HttpResponse(json.dumps(
        {
            'id': request.resource_owner.id,
            'username': request.resource_owner.username,
            'email': request.resource_owner.email,
            'first_name': request.resource_owner.first_name,
            'last_name': request.resource_owner.last_name
        }
    ), content_type="application/json")


@protected_resource(scopes=['read'])
def oauth_profile(request):
    profile = request.resource_owner.cosinnus_profile
    media_tag_fields = ['visibility', 'location',
                        'location_lat', 'location_lon',
                        'place', 'valid_start', 'valid_end',
                        'approach']

    media_tag = profile.media_tag
    media_tag_dict = {}
    if media_tag:
        for field in media_tag_fields:
            media_tag_dict[field] = getattr(media_tag, field)

    return HttpResponse(json.dumps(
        {
            'avatar': profile.avatar_url,
            'description': profile.description,
            'website': profile.website,
            'language': profile.language,
            'media_tag': media_tag_dict
        }
    ), content_type="application/json")


@api_view(['GET'])
def current_user(request):
    """
    Determine the current user by their JWT token, and return their data
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class StatisticsView(APIView):
    """
    Returns a JSON dict of common statistics for this portal
    """

    def get(self, request):
        all_users_qs = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members)
        data = {
            'groups': CosinnusSociety.objects.all_in_portal().count(),
            'projects': CosinnusProject.objects.all_in_portal().count(),
            'users_registered': all_users_qs.count(),
            'users_active': filter_active_users(all_users_qs).count(),
        }
        try:
            from cosinnus_event.models import Event
            upcoming_event_count = Event.get_current_for_portal().count()
            data.update({
                'events_upcoming': upcoming_event_count,
            })
        except:
            pass

        try:
            from cosinnus_note.models import Note
            note_count = Note.get_current_for_portal().count()
            data.update({
                'notes': note_count,
            })
        except:
            pass

        return Response(data)


oauth_current_user = OAuthUserView.as_view()
statistics = StatisticsView.as_view()
