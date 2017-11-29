# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import TemplateResolveCharField, TemplateResolveEdgeNgramField,\
    TagObjectSearchIndex, BOOSTED_FIELD_BOOST, StoredDataIndexMixin
from cosinnus.utils.user import filter_active_users
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from django.contrib.staticfiles.templatetags.staticfiles import static
    

class CosinnusGroupIndexMixin(StoredDataIndexMixin, indexes.SearchIndex):
    
    location = indexes.LocationField(null=True)
    boosted = indexes.CharField(model_attr='name', boost=BOOSTED_FIELD_BOOST)
    
    portal = indexes.IntegerField(model_attr='portal_id')
    group_members = indexes.MultiValueField(model_attr='members', indexed=False)
    public = indexes.BooleanField(model_attr='public')
    always_visible = indexes.BooleanField(default=True)
    
    def prepare_location(self, obj):
        locations = obj.locations.all()
        if locations and locations[0].location_lat and locations[0].location_lon:
            # this expects (lat,lon)!
            ret = "%s,%s" % (locations[0].location_lat, locations[0].location_lon)
            return ret
        return None
    
    def prepare_mt_location(self, obj):
        """ Groups have save their location in related model GroupLocation and not in media_tag """
        locations = obj.locations.all()
        if locations:
            return locations[0].location
        return None
        
    def prepare_mt_location_lat(self, obj):
        """ Groups have save their location in related model GroupLocation and not in media_tag """
        locations = obj.locations.all()
        if locations:
            return locations[0].location_lat
        return None
    
    def prepare_mt_location_lon(self, obj):
        """ Groups have save their location in related model GroupLocation and not in media_tag """
        locations = obj.locations.all()
        if locations:
            return locations[0].location_lon
        return None
    
    def prepare_title(self, obj):
        """ TODO: this should actually reflect the group['name'] language-sensitive magic! """
        return obj.name
    
    def prepare_url(self, obj):
        return obj.get_absolute_url()
    
    def prepare_marker_image_url(self, obj):
        return obj.get_map_marker_image_url() or static('images/group-avatar-placeholder.png')
    
    def prepare_description(self, obj):
        """ TODO: this should actually reflect the group['description'] language-sensitive magic! """
        return obj.description_long or obj.description
    
    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = qs.filter(is_active=True)
        qs = qs.select_related('media_tag').all()
        return qs
    
    def prepare(self, obj):
        """ Boost all objects of this type """
        data = super(CosinnusGroupIndexMixin, self).prepare(obj)
        data['boost'] = 1.25
        return data
    

class CosinnusProjectIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    
    def get_model(self):
        return CosinnusProject
    
    
class CosinnusSocietyIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    
    def get_model(self):
        return CosinnusSociety


class UserProfileIndex(StoredDataIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    
    boosted = indexes.CharField(model_attr='get_full_name', boost=BOOSTED_FIELD_BOOST)
    
    user_visibility_mode = indexes.BooleanField(default=True) # switch to filter differently on mt_visibility
    membership_groups = indexes.MultiValueField(model_attr='cosinnus_groups_pks') # ids of all groups the user is member/admin of
    portals = indexes.MultiValueField()
    location = indexes.LocationField(null=True)
    
    def prepare_portals(self, obj):
        return list(obj.user.cosinnus_portal_memberships.values_list('group_id', flat=True))
    
    def prepare_location(self, obj):
        if obj.media_tag and obj.media_tag.location_lat and obj.media_tag.location_lon:
            # this expects (lat,lon)!
            return "%s,%s" % (obj.media_tag.location_lat, obj.media_tag.location_lon)
        return None
    
    def prepare_title(self, obj):
        return obj.user.get_full_name()
    
    def prepare_marker_image_url(self, obj):
        return obj.get_map_marker_image_url()
    
    def get_model(self):
        return get_user_profile_model()

    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = filter_active_users(qs, filter_on_user_profile_model=True)
        qs = qs.select_related('user').all()
        return qs
    
    def prepare(self, obj):
        """ Boost all objects of this type """
        data = super(UserProfileIndex, self).prepare(obj)
        data['boost'] = 1.5
        return data
    
    