# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.conf import settings
from cosinnus.utils.search import TemplateResolveCharField, TemplateResolveEdgeNgramField,\
    TagObjectSearchIndex, BOOSTED_FIELD_BOOST, StoredDataIndexMixin,\
    DocumentBoostMixin
from cosinnus.utils.user import filter_active_users, filter_portal_users
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.contrib.auth import get_user_model
from cosinnus.utils.functions import normalize_within_stddev, resolve_class
from cosinnus.utils.group import get_cosinnus_group_model
from django.core.urlresolvers import reverse
from django.utils.functional import cached_property
from django.contrib.auth.models import AnonymousUser
from cosinnus.models.idea import CosinnusIdea
    

class CosinnusGroupIndexMixin(DocumentBoostMixin, StoredDataIndexMixin, indexes.SearchIndex):
    
    location = indexes.LocationField(null=True)
    boosted = indexes.CharField(model_attr='name', boost=BOOSTED_FIELD_BOOST)
    
    portal = indexes.IntegerField(model_attr='portal_id')
    group_members = indexes.MultiValueField(indexed=False)
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
    
    def get_image_field_for_icon(self, obj):
        return obj.get_image_field_for_icon()
    
    def get_image_field_for_background(self, obj):
        return obj.get_image_field_for_background()
    
    def prepare_description(self, obj):
        """ TODO: this should actually reflect the group['description'] language-sensitive magic! """
        return obj.description_long or obj.description
    
    def prepare_group_members(self, obj):
        if not hasattr(obj, '_group_members'):
            obj._group_members = obj.members
        return obj._group_members
    
    def prepare_member_count(self, obj):
        """ Member count for projects/groups """
        return len(self.prepare_group_members(obj))
    
    def prepare_content_count(self, obj):
        """ Upcoming events for this project/group """
        try:
            event_model = resolve_class('cosinnus_event.models.Event')
        except ImportError:
            return -1
        return event_model.get_current(obj, AnonymousUser()).count()
    
    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = qs.filter(is_active=True)
        qs = qs.select_related('media_tag').all()
        return qs
    
    def boost_model(self, obj, indexed_data):
        """ We boost by number of members this group has, normalized over
            the mean/stddev of the member count of all groups in this portal (excluded the Forum!), 
            in a range of [0.0..1.0]."""
        group = obj
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        def qs_func():
            qs = get_cosinnus_group_model().objects.all_in_portal()
            if forum_slug:
                qs = qs.exclude(slug=forum_slug)
            return qs
        
        mean, stddev = self.get_mean_and_stddev(qs_func, 'memberships')
        group_member_count = group.actual_members.count()
        members_rank = normalize_within_stddev(group_member_count, mean, stddev, stddev_factor=1.0)
        return members_rank

class CosinnusProjectIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    
    def get_model(self):
        return CosinnusProject
    
    def prepare_group_slug(self, obj):
        """ For projects assigned to a parent group, we link that group """
        return obj.parent and obj.parent.slug or None
    
    def prepare_group_name(self, obj):
        """ Stub, overridden by individual indexes """
        return obj.parent and obj.parent.name or None
    
    
class CosinnusSocietyIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    
    def get_model(self):
        return CosinnusSociety
    
    def prepare_participant_count(self, obj):
        """ child projects for groups """ 
        return obj.groups.count()


class UserProfileIndex(DocumentBoostMixin, StoredDataIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    
    boosted = indexes.CharField(model_attr='get_full_name', boost=BOOSTED_FIELD_BOOST)
    
    user_visibility_mode = indexes.BooleanField(default=True) # switch to filter differently on mt_visibility
    membership_groups = indexes.MultiValueField(model_attr='cosinnus_groups_pks') # ids of all groups the user is member/admin of
    admin_groups = indexes.MultiValueField() # ids of all groups the user is member/admin of
    portals = indexes.MultiValueField()
    location = indexes.LocationField(null=True)
    user_id = indexes.IntegerField(model_attr='user__id')
    
    def prepare_portals(self, obj):
        return list(obj.user.cosinnus_portal_memberships.values_list('group_id', flat=True))
    
    def prepare_location(self, obj):
        if obj.media_tag and obj.media_tag.location_lat and obj.media_tag.location_lon:
            # this expects (lat,lon)!
            return "%s,%s" % (obj.media_tag.location_lat, obj.media_tag.location_lon)
        return None
    
    def prepare_title(self, obj):
        return obj.user.get_full_name()
    
    def prepare_slug(self, obj):
        return obj.user.username
    
    def get_image_field_for_icon(self, obj):
        return obj.get_image_field_for_icon()
    
    def prepare_url(self, obj):
        """ NOTE: UserProfiles always contain a relative URL! """
        return reverse('cosinnus:profile-detail', kwargs={'username': obj.user.username})
    
    def prepare_member_count(self, obj):
        """ Memberships for users """
        return self._get_memberships_count(obj)
    
    def prepare_admin_groups(self, obj):
        return list(get_cosinnus_group_model().objects.get_for_user_group_admin_pks(obj.user))
    
    def get_model(self):
        return get_user_profile_model()

    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = filter_active_users(qs, filter_on_user_profile_model=True)
        qs = qs.select_related('user').all()
        return qs
    
    def _get_memberships_count(self, obj):
        if not hasattr(obj, '_memberships_count'):
            setattr(obj, '_memberships_count', obj.user.cosinnus_memberships.count())
        return obj._memberships_count
    
    def boost_model(self, obj, indexed_data):
        """ We boost by number of groups the user is a member of, normalized over
            the mean/stddev of the count of groups each portal user is a members of, 
            in a range of [0.0..1.0] """
        def qs_func():
            return filter_portal_users(filter_active_users(get_user_model().objects.all()))
        mean, stddev = self.get_mean_and_stddev(qs_func, 'cosinnus_memberships')
        user_memberships_count = self._get_memberships_count(obj)
        memberships_rank = normalize_within_stddev(user_memberships_count, mean, stddev, stddev_factor=2.0)
        return memberships_rank
    
    
class IdeaSearchIndex(DocumentBoostMixin, TagObjectSearchIndex, StoredDataIndexMixin, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True)
    boosted = indexes.EdgeNgramField(model_attr='title', boost=BOOSTED_FIELD_BOOST)

    creator = indexes.IntegerField(model_attr='creator__id', null=True)
    portal = indexes.IntegerField(model_attr='portal_id')
    location = indexes.LocationField(null=True)
    
    def get_model(self):
        return CosinnusIdea
    
    def prepare_member_count(self, obj):
        """ Group member count for taggable objects """
        if not hasattr(obj, '_like_count'):
            obj._like_count = 33
        return obj._like_count # TODO: likes
    
    def prepare_participant_count(self, obj):
        self.prepare_member_count(obj)
    
    def prepare_location(self, obj):
        if obj.media_tag and obj.media_tag.location_lat and obj.media_tag.location_lon:
            # this expects (lat,lon)!
            return "%s,%s" % (obj.media_tag.location_lat, obj.media_tag.location_lon)
        return None

    def get_image_field_for_background(self, obj):
        return obj.image
    
    def index_queryset(self, using=None):
        qs = self.get_model().objects.all_in_portal()
        qs = qs.select_related('media_tag')
        return qs
    
    def boost_model(self, obj, indexed_data):
        """ TODO boost by likes with stddev! """
        return 99
    