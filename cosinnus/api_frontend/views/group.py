from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.group import CosinnusGroupSerializer, CosinnusGroupSettingsSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import IsCosinnusGroupUser


class CosinnusGroupSettingsView(APIView):
    """An endpoint that returns configured settings/properties for a group."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsCosinnusGroupUser,)

    group = None

    def initial(self, request, *args, **kwargs):
        # get group
        group_id = kwargs.get('group_id')
        self.group = get_cosinnus_group_model().objects.filter(is_active=True, pk=group_id).first()
        if not self.group:
            raise NotFound()
        return super().initial(request, *args, **kwargs)

    def get(self, request, group_id):
        serializer = CosinnusGroupSettingsSerializer(self.group, context={'request': request})
        return Response(serializer.data)


class CosinnusGroupPersonalView(ListAPIView):
    """API to list personal user groups sorted by visit."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = CosinnusGroupSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = get_cosinnus_group_model().objects.get_personal_items(user)
        return queryset


class CosinnusGroupRecommendationsView(ListAPIView):
    """API to list group recommendations for a user."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = CosinnusGroupSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = get_cosinnus_group_model().objects.get_recommendations(user)
        return queryset
