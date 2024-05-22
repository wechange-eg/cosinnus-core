from django.utils.timezone import now
from haystack import indexes

from cosinnus.search_indexes import NestedField
from cosinnus.utils.search import (
    BOOSTED_FIELD_BOOST,
    DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE,
    DocumentBoostMixin,
    StoredDataIndexMixin,
    TagObjectSearchIndex,
    TemplateResolveCharField,
    TemplateResolveNgramField,
)
from cosinnus_organization.models import CosinnusOrganization


class OrganizationSearchIndex(DocumentBoostMixin, TagObjectSearchIndex, StoredDataIndexMixin, indexes.Indexable):
    text = TemplateResolveNgramField(document=True, model_attr='name')
    rendered = TemplateResolveCharField(use_template=True, indexed=False)

    boosted = indexes.NgramField(model_attr='name', boost=BOOSTED_FIELD_BOOST)
    location = indexes.LocationField(null=True)

    visible_for_all_authenticated_users = indexes.BooleanField()
    public = indexes.BooleanField(default=True)
    creator = indexes.IntegerField(null=True)
    portal = indexes.IntegerField(model_attr='portal_id')
    social_media = indexes.MultiValueField()
    type = indexes.IntegerField(model_attr='type')
    type_other = indexes.CharField(model_attr='type_other')
    group_members = indexes.MultiValueField()
    groups = indexes.MultiValueField()
    always_visible = indexes.BooleanField(default=True)
    dynamic_fields = NestedField(model_attr='dynamic_fields', stored=True, indexed=False)
    is_open_for_cooperation = indexes.BooleanField(model_attr='is_open_for_cooperation')

    def get_model(self):
        return CosinnusOrganization

    def prepare_creator(self, obj):
        """Returning this without using model_attr because of a haystack bug resolving lazy objects"""
        return obj.creator_id

    def prepare_visible_for_all_authenticated_users(self, obj):
        """This is hacky, but Haystack provides no method to filter
        for models in subqueries, so we set this indexed flag to be
        able to filter on for permissions"""
        return True

    def prepare_location(self, obj):
        locations = obj.locations.all()
        if locations and locations[0].location_lat and locations[0].location_lon:
            # this expects (lat,lon)!
            ret = '%s,%s' % (locations[0].location_lat, locations[0].location_lon)
            return ret
        return None

    def prepare_mt_location(self, obj):
        """Groups have save their location in related model GroupLocation and not in media_tag"""
        locations = obj.locations.all()
        if locations:
            return locations[0].location
        return None

    def prepare_mt_location_lat(self, obj):
        """Groups have save their location in related model GroupLocation and not in media_tag"""
        locations = obj.locations.all()
        if locations:
            return locations[0].location_lat
        return None

    def prepare_mt_location_lon(self, obj):
        """Groups have save their location in related model GroupLocation and not in media_tag"""
        locations = obj.locations.all()
        if locations:
            return locations[0].location_lon
        return None

    def prepare_title(self, obj):
        return obj.name

    def prepare_url(self, obj):
        return obj.get_absolute_url()

    def get_image_field_for_icon(self, obj):
        return obj.get_image_field_for_icon()

    def get_image_field_for_background(self, obj):
        return obj.get_image_field_for_background()

    def prepare_liked_user_ids(self, obj):
        return obj.get_liked_user_ids()

    def prepare_social_media(self, obj):
        return list(obj.social_media.values_list('url', flat=True))

    def prepare_group_members(self, obj):
        if not hasattr(obj, '_group_members'):
            obj._group_members = obj.members
        return obj._group_members

    def prepare_groups(self, obj):
        if not hasattr(obj, '_groups'):
            obj._groups = list(obj.groups.active_groups().values_list('group_id', flat=True))
        return obj._groups

    def index_queryset(self, using=None):
        qs = self.get_model().objects.active()
        qs = qs.select_related('media_tag')
        return qs

    def boost_model(self, obj, indexed_data):
        """We boost a single measure of 1 factor: newness (100%)."""
        age_timedelta = now() - obj.created
        organization_newness = max(1.0 - (age_timedelta.days / 90.0), 0)
        return organization_newness

    def apply_boost_penalty(self, obj, indexed_data):
        """Penaliize by 15% for not having a wallpaper image.
        @return: 1.0 for no penalty, a float in range [0.0..1.0] for a penalty
        """
        if not self.get_image_field_for_background(obj):
            return DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE
        return 1.0
