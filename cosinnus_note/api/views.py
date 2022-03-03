from rest_framework import viewsets

from cosinnus.api.views.mixins import PublicTaggableObjectFilterMixin, CosinnusFilterQuerySetMixin
from cosinnus_note.api.serializers import NoteListSerializer, NoteRetrieveSerializer
from cosinnus_note.models import Note


class NoteViewSet(CosinnusFilterQuerySetMixin,
                  PublicTaggableObjectFilterMixin,
                  viewsets.ReadOnlyModelViewSet):

    queryset = Note.objects.all()
    MANAGED_TAGS_FILTER_ON_GROUP = True

    def get_serializer_class(self):
        if self.action == 'list':
            return NoteListSerializer
        if self.action == 'retrieve':
            return NoteRetrieveSerializer
        return NoteRetrieveSerializer
