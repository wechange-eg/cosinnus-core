from rest_framework import viewsets

from cosinnus_organization.api.rdf_serializers import OrganizationRDFSerializer
from cosinnus_organization.api.serializers import OrganizationListSerializer, OrganizationRetrieveSerializer
from cosinnus.api.views import PublicCosinnusGroupFilterMixin
from cosinnus_organization.models import CosinnusOrganization
from rest_framework_rdf.viewsets import RDFViewSetMixin


class OrganizationViewSet(PublicCosinnusGroupFilterMixin,
                          RDFViewSetMixin,
                          viewsets.ReadOnlyModelViewSet):

    queryset = CosinnusOrganization.objects.public()
    serializer_class = OrganizationListSerializer
    rdf_serializer_class = OrganizationRDFSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        if self.action == 'retrieve':
            return OrganizationRetrieveSerializer
        return OrganizationRetrieveSerializer
