from rdflib import URIRef
from rdflib.namespace import Namespace, SDO

from rest_framework_rdf.serializers import RDFSerializer, RDFField, RDFSerializerMethodField

from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationLocation

WECHANGE = Namespace('http://wechange.de')
LOCN = Namespace('http://www.w3.org/ns/locn#')


class PlaceRDFSerializer(RDFSerializer):
    location_lat = RDFField(predicate=SDO.latitude)
    location_lon = RDFField(predicate=SDO.longitude)

    class Meta:
        model = CosinnusOrganizationLocation
        fields = ('location_lat', 'location_lon')
        type = SDO.Place
        prefixes = {
            'schema': SDO,
        }

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
    name = RDFField(predicate=SDO.name)
    legal_name = RDFSerializerMethodField(predicate=SDO.legalName)
    url = RDFSerializerMethodField(predicate=SDO.url)
    place = PlaceRDFSerializer(source='locations.first')
    contact_point = ContactPointRDFSerializer(source='*')

    class Meta:
        model = CosinnusOrganization
        fields = ('name', 'legal_name', 'url', 'place', 'contact_point')
        type = SDO.Organization
        prefixes = {
            'wechange': WECHANGE,
            'sdo': SDO,
        }

    def get_id(self, instance):
        return URIRef(f'{instance.get_absolute_url()}#organization')

    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_legal_name(self, obj):
        return obj.name


class CreativeWorkRDFSerializer(RDFSerializer):
    about = OrganizationRDFSerializer(source='*')
    last_modified = RDFField(predicate=SDO.dateModified)
    created = RDFField(predicate=SDO.dateCreated)
    license = RDFSerializerMethodField(predicate=SDO.license)
    keywords = RDFSerializerMethodField(predicate=SDO.keywords)
    identifier = RDFSerializerMethodField(predicate=SDO.identifier)
    url = RDFSerializerMethodField(predicate=SDO.url)
    description = RDFField(predicate=SDO.description)

    class Meta:
        model = CosinnusOrganization
        fields = ('about', 'last_modified', 'created', 'license', 'keywords',
                  'identifier', 'url', 'description')
        type = SDO.CreativeWork
        prefixes = {
            'wechange': WECHANGE,
            'sdo': SDO,
        }

    def get_id(self, instance):
        return URIRef(instance.get_absolute_url())

    def get_license(self, obj):
        return 'CC0-1.0'

    def get_keywords(self, obj):
        if hasattr(obj, 'media_tag'):
            topics = obj.media_tag.get_topics_rendered()
            tags = ','.join(obj.media_tag.tags.values_list('name', flat=True))
            return ','.join(filter(None, [topics, tags]))
        return ''

    def get_identifier(self, obj):
        return obj.get_absolute_url()

    def get_url(self, obj):
        return obj.get_absolute_url()


class PostalAddressRDFSerializer(RDFSerializer):
    location = RDFField(predicate=LOCN.fullAddress)
    # street = RDFField(predicate=LOCN.addressArea)
    # post_code = RDFField(predicate=LOCN.postCode)
    # city = RDFField(predicate=LOCN.postName)
    # state = RDFField(predicate=LOCN.adminUnitL2)
    # country = RDFField(predicate=LOCN.adminUnitL1)

    class Meta:
        model = CosinnusOrganizationLocation
        fields = ('location',)
        type = SDO.PostalAddress
        prefixes = {
            'sdo': SDO,
        }

    def get_id(self, instance):
        return URIRef(f'{instance.organization.get_absolute_url()}#postalAddress')
