from rest_framework import serializers


class DeckStackSerializer(serializers.Serializer):
    title = serializers.CharField()
    order = serializers.IntegerField()


class DeckLabelSerializer(serializers.Serializer):
    title = serializers.CharField()
    color = serializers.CharField()
