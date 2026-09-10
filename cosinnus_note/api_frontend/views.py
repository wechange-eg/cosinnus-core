from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.tagged import CosinnusTagObjectLikeSerializer
from cosinnus.api_frontend.views.mixins import ViewSetActionMixin
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus_note.api_frontend.permissions import CosinnusNoteForumPostPermissions, CosinnusNoteLikePermissions
from cosinnus_note.api_frontend.serializers import CosinnusNoteForumPostSerializer, CosinnusNoteSerializer
from cosinnus_note.models import Note


class CosinnusNoteViewSet(ViewSetActionMixin, viewsets.GenericViewSet):
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
        queryset = Note.objects.get_readable_items(user)
        return queryset

    def get_serializer_class(self):
        """Get serializer based on viewset action."""
        action_serializers = {
            'forum_post': CosinnusNoteForumPostSerializer,
            'like': CosinnusTagObjectLikeSerializer,
        }
        if self.action in action_serializers:
            return action_serializers[self.action]
        return self.serializer_class

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def personal(self, request):
        """Return personal notes for user."""
        queryset = Note.objects.get_personal_items(request.user)
        return self.list_action_response(request, queryset)

    @action(
        detail=False,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def recommendations(self, request):
        """Return recommendations for user."""
        queryset = Note.objects.get_recommendations(request.user)
        return self.list_action_response(request, queryset)

    @action(
        detail=False,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusNoteForumPostPermissions],
    )
    def forum_post(self, request):
        """Create a forum group post."""
        return self.list_action_response(request)

    @action(
        detail=True,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusNoteLikePermissions],
    )
    def like(self, request, pk):
        """Like / unlike a note."""
        return self.detail_action_response(request)
