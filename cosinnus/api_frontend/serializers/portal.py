import logging

from rest_framework import serializers

from cosinnus.models.managed_tags import CosinnusManagedTag, \
    CosinnusManagedTagType


logger = logging.getLogger('cosinnus')


class CosinnusManagedTagTypeSerializer(serializers.ModelSerializer):
    """ Serializer for the User Login API endpoint """
    
    class Meta(object):
        model = CosinnusManagedTagType
        fields = ('id', 'name', 'prefix_label', 'color')
        read_only_fields = fields
    


class CosinnusManagedTagSerializer(serializers.ModelSerializer):
    """ Serializer for the User Login API endpoint """
    
    type = CosinnusManagedTagTypeSerializer(many=False)
    group_url = serializers.URLField(source='paired_group_url')
    
    class Meta(object):
        model = CosinnusManagedTag
        fields = ('slug', 'name', 'type', 'description', 'image', 'url', 'search_synonyms', 
                  'group_url')
        read_only_fields = fields

    