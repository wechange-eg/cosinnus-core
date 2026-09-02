from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus_note.api_frontend.serializers import CosinnusNoteSerializer
from cosinnus_note.models import Note


class CosinnusNoteViewSet(viewsets.ReadOnlyModelViewSet):
    """Note api for v3."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusNoteSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Note.objects.get_personal_items(user)
        return queryset

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def recommendations(self, request):
        """Return recommendations for user."""
        queryset = Note.objects.get_recommendations(request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
