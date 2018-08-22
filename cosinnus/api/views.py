from django.db.models import Q
from rest_framework import viewsets

from cosinnus.models.group import CosinnusGroup
from cosinnus.models.group_extra import CosinnusProject
from cosinnus.models.tagged import BaseTagObject
from .serializers import CosinnusGroupSerializer, CosinnusProjectSerializer


class CosinnusGroupSerializerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CosinnusGroup.objects.all()
    serializer_class = CosinnusGroupSerializer

    def get_queryset(self):
        """
        Optionally filter by group
        FIXME: Use generic filters here after upgrade to django-filter==0.15.0
        """
        queryset = self.queryset
        # Filter visibility
        queryset = queryset.filter(is_active=True, public=True)
        queryset = queryset.filter(Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL) |
                                   Q(
                                       Q(
                                           Q(media_tag__isnull=True) |
                                           Q(media_tag__visibility__isnull=True)
                                       ),
                                       parent__media_tag__visibility = BaseTagObject.VISIBILITY_ALL
                                   ))
        # Overwrite ugly but commonly used filters
        FILTER_MAP = {
            'tags': 'media_tag__tags__name'
        }
        for key, value in self.request.query_params.items():
            key = FILTER_MAP.get(key, key)
            if value is not None:
                queryset = queryset.filter(**{key: value})
        return queryset


class CosinnusProjectSerializerViewSet(CosinnusGroupSerializerViewSet):
    queryset = CosinnusProject.objects.all()
    serializer_class = CosinnusProjectSerializer
