from django.urls import reverse
from rest_framework import serializers

from cosinnus.api.serializers.group import CosinnusLocationSerializer
from cosinnus_organization.models import CosinnusOrganization


class OrganizationListSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.SerializerMethodField()
    url = serializers.URLField(source='get_absolute_url', read_only=True)
    timestamp = serializers.DateTimeField(source='last_modified')
    image = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    # admins = serializers.SerializerMethodField()
    locations = CosinnusLocationSerializer(many=True)

    class Meta(object):
        model = CosinnusOrganization
        fields = ('id', 'url', 'slug', 'name', 'description', 'website', 'admins', 'locations', 'timestamp', 'topics',
                  'tags', 'image')

    def get_id(self, obj):
        url = reverse('cosinnus:api:organization-detail', kwargs={'slug': obj.slug})
        return self.context['request'].build_absolute_uri(url)[:-1]

    def get_image(self, obj):
        if not obj.avatar:
            return None
        return self.context['request'].build_absolute_uri(obj.avatar.url)

    def get_topics(self, obj):
        return obj.media_tag.get_topics()

    def get_tags(self, obj):
        return obj.media_tag.tags.values_list('name', flat=True)

    # def get_admins(self, obj):
    #     queryset = obj.actual_admins
    #     # Show only public admins
    #     queryset = queryset.filter(cosinnus_profile__media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
    #     return queryset.values_list('email', flat=True)


class OrganizationRetrieveSerializer(OrganizationListSerializer):
    pass


class OrganizationSimpleSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = CosinnusOrganization
        fields = ('id', 'name', 'slug', 'description')
