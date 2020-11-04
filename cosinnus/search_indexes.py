# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from haystack import indexes

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
from django.utils.timezone import now

from cosinnus.utils.search import TemplateResolveCharField, TemplateResolveNgramField,\
    TagObjectSearchIndex, BOOSTED_FIELD_BOOST, StoredDataIndexMixin,\
    DocumentBoostMixin, CommaSeperatedIntegerMultiValueField,\
    LocalCachedIndexMixin, DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE
from cosinnus.utils.user import filter_active_users, filter_portal_users
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.utils.functions import normalize_within_stddev, resolve_class
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_ids
from cosinnus.models.idea import CosinnusIdea
from cosinnus_organization.models import CosinnusOrganization
    

class CosinnusGroupIndexMixin(LocalCachedIndexMixin, DocumentBoostMixin, StoredDataIndexMixin, indexes.SearchIndex):
    
    location = indexes.LocationField(null=True)
    boosted = indexes.CharField(model_attr='name', boost=BOOSTED_FIELD_BOOST)
    
    portal = indexes.IntegerField(model_attr='portal_id')
    group_members = indexes.MultiValueField(indexed=False)
    sdgs = indexes.MultiValueField(model_attr='sdgs', null=True)
    managed_tags = indexes.MultiValueField()
    public = indexes.BooleanField(model_attr='public')
    always_visible = indexes.BooleanField(default=True)
    created = indexes.DateTimeField(model_attr='created')
    group = indexes.IntegerField(model_attr='id')
    # for filtering on this model
    is_group_model = indexes.BooleanField(default=True)
    
    local_cached_attrs = ['_group_members']
    
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
    
    def prepare_managed_tags(self, obj):
        return obj.get_managed_tag_ids()
    
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
        """ We boost a combined measure of 2 added factors: newness (50%) and group member rank (50%).
            This means that a new group with lots of members will rank highest and an old group with no members lowest.
            But it also means that new groups with no members will still rank quite high, as will old groups with lots
            of members.
            
            Factors:
            - 50%: number of members this group has, normalized over
            the mean/stddev of the member count of all groups in this portal (excluded the Forum!), 
            in a range of [0.0..1.0]
            - 50%: the group's created date, highest being now() and lowest >= 3 months
            """
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
        
        age_timedelta = now() - obj.created
        group_newness = max(1.0 - (age_timedelta.days/90.0), 0) 
        
        return (members_rank / 2.0) + (group_newness / 2.0)
    
    def apply_boost_penalty(self, obj, indexed_data):
        """ Penaliize by 15% for not having a wallpaper image.
            @return: 1.0 for no penalty, a float in range [0.0..1.0] for a penalty
        """
        if not self.get_image_field_for_background(obj):
            return DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE
        return 1.0
    
    
class CosinnusProjectIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
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
    
    text = TemplateResolveNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    
    def get_model(self):
        return CosinnusSociety
    
    def prepare_participant_count(self, obj):
        """ child projects for groups """ 
        return obj.groups.count()


class UserProfileIndex(LocalCachedIndexMixin, DocumentBoostMixin, StoredDataIndexMixin, 
           TagObjectSearchIndex, indexes.Indexable):
    text = TemplateResolveNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    
    boosted = indexes.CharField(model_attr='get_full_name', boost=BOOSTED_FIELD_BOOST)
    
    user_visibility_mode = indexes.BooleanField(default=True) # switch to filter differently on mt_visibility
    membership_groups = indexes.MultiValueField() # ids of all groups the user is member/admin of
    admin_groups = indexes.MultiValueField() # ids of all groups the user is member/admin of
    admin_organizations = indexes.MultiValueField() # ids of all organizations the user is member/admin of
    portals = indexes.MultiValueField()
    location = indexes.LocationField(null=True)
    managed_tags = indexes.MultiValueField()
    user_id = indexes.IntegerField(model_attr='user__id')
    created = indexes.DateTimeField(model_attr='user__date_joined')

    local_cached_attrs = ['_memberships_count']
    
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
    
    def prepare_managed_tags(self, obj):
        return obj.get_managed_tag_ids()
    
    def prepare_url(self, obj):
        """ NOTE: UserProfiles always contain a relative URL! """
        return reverse('cosinnus:profile-detail', kwargs={'username': obj.user.username})
    
    def prepare_membership_groups(self, obj):
        """ Better to convert this QS to native list """
        group_ids = list(obj.cosinnus_groups_pks)
        if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False):
            group_ids = [pk for pk in group_ids if not pk in get_default_user_group_ids()]
        return group_ids
    
    def prepare_member_count(self, obj):
        """ Memberships for users """
        return self._get_memberships_count(obj)
    
    def prepare_admin_groups(self, obj):
        return list(get_cosinnus_group_model().objects.get_for_user_group_admin_pks(obj.user))

    def prepare_admin_organizations(self, obj):
        return list(CosinnusOrganization.objects.get_for_user_group_admin_pks(obj.user))

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
    
    def apply_boost_penalty(self, obj, indexed_data):
        """ Penaliize by 15% for not having an avatar image.
            @return: 1.0 for no penalty, a float in range [0.0..1.0] for a penalty
        """
        if not self.get_image_field_for_icon(obj):
            return DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE
        return 1.0
    
    
class IdeaSearchIndex(LocalCachedIndexMixin, DocumentBoostMixin, TagObjectSearchIndex, 
          StoredDataIndexMixin, indexes.Indexable):
    
    text = TemplateResolveNgramField(document=True, use_template=True)
    boosted = indexes.NgramField(model_attr='title', boost=BOOSTED_FIELD_BOOST)

    public = indexes.BooleanField(model_attr='public')
    visible_for_all_authenticated_users = indexes.BooleanField()
    creator = indexes.IntegerField(null=True)
    portal = indexes.IntegerField(model_attr='portal_id')
    location = indexes.LocationField(null=True)
    liked_user_ids = CommaSeperatedIntegerMultiValueField(indexed=False, stored=True)
    
    local_cached_attrs = ['_like_count', '_liked_ids']
    
    def get_model(self):
        return CosinnusIdea
    
    def prepare_creator(self, obj):
        """ Returning this without using model_attr because of a haystack bug resolving lazy objects """
        return obj.creator_id
    
    def prepare_visible_for_all_authenticated_users(self, obj):
        """ This is hacky, but Haystack provides no method to filter
            for models in subqueries, so we set this indexed flag to be
            able to filter on for permissions """
        return True
    
    def prepare_liked_user_ids(self, obj):
        return obj.get_liked_user_ids()
    
    def prepare_participant_count(self, obj):
        """ Group member count for taggable objects """
        return obj.like_count
    
    def prepare_member_count(self, obj):
        return self.prepare_participant_count(obj)
        
    def prepare_content_count(self, obj):
        return obj.created_groups.filter(is_active=True).count()
    
    def prepare_location(self, obj):
        if obj.media_tag and obj.media_tag.location_lat and obj.media_tag.location_lon:
            # this expects (lat,lon)!
            return "%s,%s" % (obj.media_tag.location_lat, obj.media_tag.location_lon)
        return None

    def get_image_field_for_background(self, obj):
        return obj.image
    
    def index_queryset(self, using=None):
        qs = self.get_model().objects.active()
        qs = qs.select_related('media_tag')
        return qs
    
    def boost_model(self, obj, indexed_data):
        """ We boost a combined measure of 2 added factors: newness (50%) and like count (50%).
            This means that a new idea with lots of likes will rank highest and an old idea with no likes lowest.
            But it also means that new ideas with no likes will still rank quite high, as will old ideas with lots
            of likes.
            
            Factors:
            - 50%: the idea's like count, normalized over the mean/stddev of the like count of all other ideas, 
                in a range of [0.0..1.0]
            - 50%: the idea's created date, highest being now() and lowest >= 3 months
            """
        
        def qs_func():
            return CosinnusIdea.objects.all_in_portal().annotate_likes()
        
        mean, stddev = self.get_mean_and_stddev(qs_func, 'like_count', non_annotated_property=True)
        current_like_count = obj.likes.filter(liked=True).count()
        members_rank_from_likes = normalize_within_stddev(current_like_count, mean, stddev, stddev_factor=1.0)
        
        age_timedelta = now() - obj.created
        members_rank_from_date = max(1.0 - (age_timedelta.days/90.0), 0) 
        
        return (members_rank_from_likes / 2.0) + (members_rank_from_date / 2.0)
    
    def apply_boost_penalty(self, obj, indexed_data):
        """ Penaliize by 15% for not having a wallpaper image.
            @return: 1.0 for no penalty, a float in range [0.0..1.0] for a penalty
        """
        if not self.get_image_field_for_background(obj):
            return DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE
        return 1.0


# also import all external search indexes
from cosinnus.external.search_indexes import * #noqa