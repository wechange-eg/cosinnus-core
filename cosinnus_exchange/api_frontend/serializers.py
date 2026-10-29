from rest_framework import serializers


class CosinnusExternalResourceSerializer(serializers.Serializer):
    """v3 external resource serializer."""

    title = serializers.CharField()
    subtitle = serializers.SerializerMethodField()
    url = serializers.URLField()

    def get_subtitle(self, obj):
        subtitle = obj.get('organization')
        if not subtitle:
            subtitle = obj.get('source')
        return subtitle
