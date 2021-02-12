from rest_framework import viewsets

from cosinnus_organization.api.serializers import OrganizationListSerializer, OrganizationRetrieveSerializer
from cosinnus.api.views.mixins import PublicCosinnusGroupFilterMixin
from cosinnus.models.group_extra import CosinnusProject


class OrganizationViewSet(PublicCosinnusGroupFilterMixin,
                          viewsets.ReadOnlyModelViewSet):

    queryset = CosinnusProject.objects.all()
    serializer_class = OrganizationListSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        if self.action == 'retrieve':
            return OrganizationRetrieveSerializer
        return OrganizationRetrieveSerializer