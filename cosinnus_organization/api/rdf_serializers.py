from rdflib import URIRef
from rdflib.namespace import Namespace
from rest_framework.reverse import reverse

from rest_framework_rdf.serializers import RDFSerializer, RDFField, RDFSerializerMethodField

from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationLocation

WECHANGE = Namespace('http://wechange.de')
SDO = Namespace('http://schema.org/')


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
        url = reverse('cosinnus:api:organization-detail', kwargs={'slug': instance.organization.slug})
        return URIRef(f'{self.context["request"].build_absolute_uri(url)}#location')


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
        url = reverse('cosinnus:api:organization-detail', kwargs={'slug': instance.slug})
        return URIRef(f'{self.context["request"].build_absolute_uri(url)}#contactPoint')


class OrganizationRDFSerializer(RDFSerializer):
    name = RDFField(predicate=SDO.name)
    legal_name = RDFSerializerMethodField(predicate=SDO.legalName)
    url = RDFSerializerMethodField(predicate=SDO.url)
    place = PlaceRDFSerializer(source='locations.first', predicate=SDO.location)
    contact_point = ContactPointRDFSerializer(source='*', predicate=SDO.contactPoint)

    class Meta:
        model = CosinnusOrganization
        fields = ('name', 'legal_name', 'url', 'place', 'contact_point')
        type = SDO.Organization
        prefixes = {
            'wechange': WECHANGE,
            'sdo': SDO,
        }

    def get_id(self, instance):
        url = reverse('cosinnus:api:organization-detail', kwargs={'slug': instance.slug})
        return URIRef(f'{self.context["request"].build_absolute_uri(url)}#organization')

    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_legal_name(self, obj):
        return obj.name


class CreativeWorkRDFSerializer(RDFSerializer):
    about = OrganizationRDFSerializer(source='*', predicate=SDO.about)
    last_modified = RDFSerializerMethodField(predicate=SDO.dateModified)
    created = RDFSerializerMethodField(predicate=SDO.dateCreated)
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
        url = reverse('cosinnus:api:organization-detail', kwargs={'slug': instance.slug})
        return URIRef(self.context["request"].build_absolute_uri(url))

    def get_license(self, obj):
        return 'CC0-1.0'

    def get_keywords(self, obj):
        if hasattr(obj, 'media_tag'):
            topics = obj.media_tag.get_topics_rendered()
            tags = ','.join(obj.media_tag.tags.values_list('name', flat=True))
            return ','.join(filter(None, [topics, tags])).lower()
        return ''

    def get_identifier(self, obj):
        return obj.get_absolute_url()

    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_created(self, obj):
        return obj.created and obj.created.isoformat() or None

    def get_last_modified(self, obj):
        return obj.last_modified and obj.last_modified.isoformat() or None


class PostalAddressRDFSerializer(RDFSerializer):
    location = RDFField(predicate=SDO.fullAddress)
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
        url = reverse('cosinnus:api:organization-detail', kwargs={'slug': instance.organization.slug})
        return URIRef(f'{self.context["request"].build_absolute_uri(url)}#postalAdress')
