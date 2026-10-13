from rest_framework import serializers

from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus_marketplace.models import Offer


class CosinnusOfferSerializer(CosinnusBaseTaggableObjectSerializer):
    """v3 offer serializer."""

    type = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = (
            'id',
            'type',
            'title',
            'creator',
            'created',
            'group',
            'url',
        )

    def get_type(self, obj):
        type_map = {
            Offer.TYPE_BUYING: 'request',
            Offer.TYPE_SELLING: 'offer',
        }
        return type_map[obj.type]
