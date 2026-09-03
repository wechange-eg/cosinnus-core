from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.views.mixins import ViewSetActionMixin
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus_poll.api_frontend.serializers import CosinnusPollSerializer
from cosinnus_poll.models import Poll


class CosinnusPollViewSet(ViewSetActionMixin, viewsets.ReadOnlyModelViewSet):
    """Poll api for v3."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusPollSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Poll.objects.get_personal_items(user)
        return queryset

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def open(self, request):
        """Return open polls where the user has not voted yet."""
        queryset = Poll.objects.get_personal_open_polls(request.user)
        return self.list_action_response(queryset)
