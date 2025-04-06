from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, viewsets

from cosinnus.api.views.mixins import CosinnusFilterQuerySetMixin, PublicTaggableObjectFilterMixin
from cosinnus_note.api.serializers import NoteListSerializer, NoteRetrieveSerializer
from cosinnus_note.models import Note


class MyQueryParamSerializer(serializers.Serializer):
    my_name = serializers.CharField()
    my_number = serializers.IntegerField(help_text='Some custom description for the number')
    my_bool = serializers.BooleanField()


class NoteViewSet(CosinnusFilterQuerySetMixin, PublicTaggableObjectFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    An endpoint that returns publicly visible news posts.
    """

    queryset = Note.objects.all()
    MANAGED_TAGS_FILTER_ON_GROUP = True

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'group_id',
                openapi.IN_QUERY,
                description='If provided, will only return items belonging to the group/project with the given '
                'group id. Group ids are displayed in the `/groups/` and `/projects/` endpoints.',
                type=openapi.TYPE_INTEGER,
            ),
        ],
    )
    def list(self, request, **kwargs):
        return super().list(request, **kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return NoteListSerializer
        if self.action == 'retrieve':
            return NoteRetrieveSerializer
        return NoteRetrieveSerializer
