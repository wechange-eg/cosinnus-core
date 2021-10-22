from rest_framework import viewsets

from cosinnus.api.serializers.group import CosinnusSocietySerializer, CosinnusProjectSerializer
from cosinnus.api.views.mixins import PublicCosinnusGroupFilterMixin, CosinnusFilterQuerySetMixin, \
    ReadOnlyOrIsAdminUser, GetForUserViewSetMixin
from cosinnus.conf import settings
from cosinnus.models import RelatedGroups
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.utils.group import get_cosinnus_group_model

CosinnusGroup = get_cosinnus_group_model()


class CosinnusSocietyViewSet(CosinnusFilterQuerySetMixin,
                             PublicCosinnusGroupFilterMixin,
                             GetForUserViewSetMixin,
                             viewsets.ModelViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('society', ['get', ])
    permission_classes = (ReadOnlyOrIsAdminUser,)
    queryset = CosinnusSociety.objects.all()
    serializer_class = CosinnusSocietySerializer

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # Add related groups
        for related_slug in self.request.data.get('related', []):
            related_group = CosinnusGroup.objects.filter(slug=related_slug).first()
            if not related_group:
                continue
            RelatedGroups.objects.get_or_create(from_group=serializer.instance, to_group=related_group)
            RelatedGroups.objects.get_or_create(from_group=related_group, to_group=serializer.instance)


class CosinnusProjectViewSet(CosinnusSocietyViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('project', ['get', ])
    permission_classes = (ReadOnlyOrIsAdminUser,)
    queryset = CosinnusProject.objects.all()
    serializer_class = CosinnusProjectSerializer
