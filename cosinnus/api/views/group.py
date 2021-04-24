from rest_framework import viewsets

from cosinnus.api.serializers.group import CosinnusSocietySerializer, CosinnusProjectSerializer
from cosinnus.api.views.mixins import PublicCosinnusGroupFilterMixin, CosinnusFilterQuerySetMixin, ReadOnlyOrIsAdminUser
from cosinnus.conf import settings
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject


class CosinnusSocietyViewSet(CosinnusFilterQuerySetMixin,
                             PublicCosinnusGroupFilterMixin,
                             viewsets.ModelViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('society', ['get', ])
    permission_classes = (ReadOnlyOrIsAdminUser,)
    queryset = CosinnusSociety.objects.all()
    serializer_class = CosinnusSocietySerializer


class CosinnusProjectViewSet(CosinnusSocietyViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('project', ['get', ])
    permission_classes = (ReadOnlyOrIsAdminUser,)
    queryset = CosinnusProject.objects.all()
    serializer_class = CosinnusProjectSerializer
