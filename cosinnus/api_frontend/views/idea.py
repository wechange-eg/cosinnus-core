from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.idea import CosinnusIdeaSerializer
from cosinnus.api_frontend.views.mixins import ViewSetActionMixin
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.models.idea import CosinnusIdea


class CosinnusIdeaViewSet(ViewSetActionMixin, viewsets.ReadOnlyModelViewSet):
    """Idea api for v3."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusIdeaSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = CosinnusIdea.objects.get_personal_items(user)
        return queryset

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def liked(self, request):
        """Return liked ideas."""
        queryset = CosinnusIdea.objects.get_personal_liked_items(request.user)
        return self.list_action_response(queryset)

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def recommendations(self, request):
        """Return recommended ideas."""
        queryset = CosinnusIdea.objects.get_recommendations(request.user)
        return self.list_action_response(queryset)
