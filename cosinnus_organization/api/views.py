from rest_framework import viewsets

from cosinnus.conf import settings
from cosinnus_organization.api.rdf_serializers import CreativeWorkRDFSerializer
from cosinnus_organization.api.serializers import OrganizationListSerializer, OrganizationRetrieveSerializer
from cosinnus_organization.models import CosinnusOrganization
from cosinnus.api.views.mixins import PublicCosinnusGroupFilterMixin, ReadOnlyOrIsAdminUser, CosinnusFilterQuerySetMixin
from rest_framework_rdf.viewsets import RDFViewSetMixin


class OrganizationViewSet(PublicCosinnusGroupFilterMixin,
                          CosinnusFilterQuerySetMixin,
                          RDFViewSetMixin,
                          viewsets.ModelViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('organization', ['get', ])
    permission_classes = (ReadOnlyOrIsAdminUser,)
    queryset = CosinnusOrganization.objects.public()
    rdf_serializer_class = CreativeWorkRDFSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        if self.action == 'retrieve':
            return OrganizationRetrieveSerializer
        return OrganizationRetrieveSerializer
