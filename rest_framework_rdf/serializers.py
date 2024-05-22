from rdflib import RDF, Literal, URIRef
from rest_framework import serializers
from rest_framework.fields import Field, SerializerMethodField


class RDFFieldMixin:
    predicate = None
    lang = None
    datatype = None
    normalize = None

    def __init__(self, *args, **kwargs):
        self.predicate = kwargs.pop('predicate')
        self.lang = kwargs.pop('lang', None)
        self.datatype = kwargs.pop('datatype', None)
        self.normalize = kwargs.pop('normalize', None)
        super().__init__(*args, **kwargs)


class RDFField(RDFFieldMixin, Field):
    def to_representation(self, value):
        literal = Literal(value, lang=self.lang, datatype=self.datatype, normalize=self.normalize)
        return self.parent.id, self.predicate, literal


class RDFSerializerMethodField(RDFFieldMixin, SerializerMethodField):
    def to_representation(self, value):
        method = getattr(self.parent, self.method_name)
        literal = Literal(method(value), lang=self.lang, datatype=self.datatype, normalize=self.normalize)
        return self.parent.id, self.predicate, literal


class RDFSerializer(serializers.ModelSerializer):
    serializer_field_mapping = {}
    predicate = None

    id = None

    def __init__(self, *args, **kwargs):
        self.predicate = kwargs.pop('predicate', None)
        super().__init__(*args, **kwargs)

    def get_id(self, instance):
        if hasattr(instance, 'get_absolute_url'):
            return URIRef(instance.get_absolute_url())
        return URIRef(instance.id)

    def to_representation(self, instance):
        self.id = self.get_id(instance)
        prefixes = hasattr(self.Meta, 'prefixes') and self.Meta.prefixes or {}
        resources = []
        for field_name, resource in super().to_representation(instance).items():
            if isinstance(resource, dict):
                resources.append(resource['type'])
                prefixes.update(resource['prefixes'])
                resources += resource['resources']
                serializer_predicate = self.fields[field_name].predicate or resource['type'][2]
                resources.append((self.id, serializer_predicate, resource['type'][0]))
            elif resource:
                resources.append(resource)
        return {
            'type': (self.id, RDF.type, self.Meta.type),
            'prefixes': prefixes,
            'resources': resources,
        }

    class Meta:
        type = None
        prefixes = {}
