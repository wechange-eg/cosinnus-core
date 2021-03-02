from rdflib import Literal, URIRef, RDF
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField, Field


class RDFFieldMixin:
    predicate = None

    def __init__(self, *args, **kwargs):
        self.predicate = kwargs.pop('predicate')
        super().__init__(*args, **kwargs)


class RDFField(RDFFieldMixin, Field):
    def to_representation(self, value):
        return self.parent.id, self.predicate, Literal(value)


class RDFSerializerMethodField(RDFFieldMixin, SerializerMethodField):
    def to_representation(self, value):
        method = getattr(self.parent, self.method_name)
        return self.parent.id, self.predicate, Literal(method(value))


class RDFSerializer(serializers.ModelSerializer):
    serializer_field_mapping = {}

    id = None

    def get_id(self, instance):
        if hasattr(instance, 'get_absolute_url'):
            return URIRef(instance.get_absolute_url())
        return URIRef(instance.id)

    def to_representation(self, instance):
        self.id = self.get_id(instance)
        prefixes = hasattr(self.Meta, 'prefixes') and self.Meta.prefixes or {}
        resources = []
        for resource in super().to_representation(instance).values():
            if isinstance(resource, dict):
                resources.append(resource['type'])
                prefixes.update(resource['prefixes'])
                resources += resource['resources']
                resources.append((self.id, resource['type'][2], resource['type'][0]))
            elif resource:
                resources.append(resource)
        return {
            "type": (self.id, RDF.type, self.Meta.type),
            "prefixes": prefixes,
            "resources": resources,
        }

    class Meta:
        type = None
        prefixes = {}
