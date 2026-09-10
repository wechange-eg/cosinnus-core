from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.views.mixins import ViewSetActionMixin
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus_event.api_frontend.serializers import CosinnusEventPollSerializer, CosinnusEventSerializer
from cosinnus_event.models import Event


class CosinnusEventPollViewSet(ViewSetActionMixin, viewsets.GenericViewSet):
    """Event poll api for v3."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusEventPollSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Event.objects.none()

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def open(self, request):
        """Return open polls where the user has not voted yet."""
        queryset = Event.objects.get_personal_open_polls(request.user)
        return self.list_action_response(request, queryset)


class CosinnusEventViewSet(ViewSetActionMixin, viewsets.GenericViewSet):
    """Event api for v3."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Event.objects.none()

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def attending(self, request):
        """Return attending upcoming user events."""
        queryset = Event.objects.get_personal_attending_events(request.user)
        return self.list_action_response(request, queryset)

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def recommendations(self, request):
        """Return user public event recommendations."""
        queryset = Event.objects.get_recommendations(request.user)
        return self.list_action_response(request, queryset)
