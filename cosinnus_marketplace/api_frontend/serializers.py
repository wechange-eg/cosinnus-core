from cosinnus.api_frontend.serializers.tagged import CosinnusBaseTaggableObjectSerializer
from cosinnus_marketplace.models import Offer
from rest_framework_rdf import serializers


class CosinnusOfferSerializer(CosinnusBaseTaggableObjectSerializer):
    """Readonly v3 note serializer."""

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
