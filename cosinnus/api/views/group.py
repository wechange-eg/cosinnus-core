from rest_framework import viewsets

from cosinnus.api.serializers.group import CosinnusSocietySerializer, CosinnusProjectSerializer
from cosinnus.api.views.mixins import PublicCosinnusGroupFilterMixin, CosinnusFilterQuerySetMixin
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject


class CosinnusSocietyViewSet(CosinnusFilterQuerySetMixin,
                             PublicCosinnusGroupFilterMixin,
                             viewsets.ReadOnlyModelViewSet):
    queryset = CosinnusSociety.objects.all()
    serializer_class = CosinnusSocietySerializer


class CosinnusProjectViewSet(CosinnusSocietyViewSet):

    queryset = CosinnusProject.objects.all()
    serializer_class = CosinnusProjectSerializer
