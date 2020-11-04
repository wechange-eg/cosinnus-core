from rest_framework import serializers


class ExternalEventSerializer(serializers.HyperlinkedModelSerializer):

    class Meta(object):
        model = None