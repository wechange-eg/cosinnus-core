from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.views.mixins import ViewSetActionMixin
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus_event.api_frontend.serializers import CosinnusEventPollSerializer, CosinnusEventSerializer
from cosinnus_event.models import Event


class CosinnusEventPollViewSet(ViewSetActionMixin, viewsets.ReadOnlyModelViewSet):
    """Event poll api for v3."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusEventPollSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Event.objects.get_personal_items(user).filter(state=Event.STATE_VOTING_OPEN)
        return queryset

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def open(self, request):
        """Return open polls where the user has not voted yet."""
        queryset = Event.objects.get_personal_open_polls(request.user)
        return self.list_action_response(queryset)


class CosinnusEventViewSet(ViewSetActionMixin, viewsets.ReadOnlyModelViewSet):
    """Event api for v3."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Event.objects.get_personal_items(user).filter(state=Event.STATE_SCHEDULED)
        return queryset

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def attending(self, request):
        """Return attending upcoming user events."""
        queryset = Event.objects.get_personal_attending_events(request.user)
        return self.list_action_response(queryset)
