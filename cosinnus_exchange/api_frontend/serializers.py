from rest_framework import serializers


class CosinnusExternalResourceSerializer(serializers.Serializer):
    """v3 external resource serializer."""

    title = serializers.CharField()
    subtitle = serializers.CharField(source='source')
    url = serializers.URLField()
