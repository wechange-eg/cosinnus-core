from rdflib import URIRef
from rdflib.namespace import Namespace, DCTERMS, FOAF, OWL, SDO

from rest_framework_rdf.serializers import RDFSerializer, RDFField, RDFSerializerMethodField

from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationLocation

WECHANGE = Namespace('http://wechange.de')
LOCN = Namespace('http://www.w3.org/ns/locn#')


class GeometryRDFSerializer(RDFSerializer):
    location_lat = RDFField(predicate=SDO.latitude)
    location_lon = RDFField(predicate=SDO.longitude)

    class Meta:
        model = CosinnusOrganizationLocation
        fields = ('location_lat', 'location_lon')
        type = LOCN.Geometry
        prefixes = {
            'schema': SDO,
        }

    def get_id(self, instance):
        return URIRef(f'{instance.organization.get_absolute_url()}#geometry')


class AddressRDFSerializer(RDFSerializer):
    location = RDFField(predicate=LOCN.fullAddress)
    # street = RDFField(predicate=LOCN.addressArea)
    # post_code = RDFField(predicate=LOCN.postCode)
    # city = RDFField(predicate=LOCN.postName)
    # state = RDFField(predicate=LOCN.adminUnitL2)
    # country = RDFField(predicate=LOCN.adminUnitL1)

    class Meta:
        model = CosinnusOrganizationLocation
        fields = ('location',)
        type = LOCN.Address
        prefixes = {
            'locn': LOCN,
        }

    def get_id(self, instance):
        return URIRef(f'{instance.organization.get_absolute_url()}#address')


class LocationRDFSerializer(RDFSerializer):
    geometry = GeometryRDFSerializer(source='*')
    address = AddressRDFSerializer(source='*')

    class Meta:
        model = CosinnusOrganizationLocation
        fields = ('geometry', 'address')
        type = DCTERMS.Location
        prefixes = {}

    def get_id(self, instance):
        return URIRef(f'{instance.organization.get_absolute_url()}#location')


class ContactPointRDFSerializer(RDFSerializer):
    email = RDFField(predicate=SDO.email)
    phone_number = RDFField(predicate=SDO.telephone)

    class Meta:
        model = CosinnusOrganization
        fields = ('email', 'phone_number')
        type = SDO.ContactPoint
        prefixes = {
            'schema': SDO,
        }

    def get_id(self, instance):
        return URIRef(f'{instance.get_absolute_url()}#contactPoint')


class OrganizationRDFSerializer(RDFSerializer):
    location = LocationRDFSerializer(source='locations.first')
    contact_point = ContactPointRDFSerializer(source='*')
    id = RDFField(predicate=DCTERMS.identifier)
    name = RDFField(predicate=FOAF.name)
    website = RDFField(predicate=FOAF.homepage)
    version_info = RDFSerializerMethodField(predicate=OWL.versionInfo)
    description = RDFField(predicate=DCTERMS.description)

    class Meta:
        model = CosinnusOrganization
        fields = ('id', 'name', 'website', 'version_info', 'description',
                  'location', 'contact_point')
        type = FOAF.Group
        prefixes = {
            'wechange': WECHANGE,
            'foaf': FOAF,
            'dcterms': DCTERMS,
            'owl': OWL,
        }

    def get_version_info(self, obj):
        return 1
