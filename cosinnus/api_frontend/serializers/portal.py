import logging

from rest_framework import serializers

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
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
        fields = ('slug', 'name', 'default', 'type', 'description', 'image', 'url', 'search_synonyms',
                  'group_url')
        read_only_fields = fields
    
    default = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    def get_default(self, obj):
        return bool(obj.slug == settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG)
    
    def get_image(self, obj):
        return f'{CosinnusPortal.get_current().get_domain()}{obj.image.url}' if obj.image else None
        
    

    