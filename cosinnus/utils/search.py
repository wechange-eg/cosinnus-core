# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

from builtins import object
from django.template import loader, Context

from haystack import indexes
from haystack.exceptions import SearchFieldError

from cosinnus.conf import settings
from cosinnus.utils.import_utils import import_from_settings
from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.functions import ensure_list_of_ints,\
    normalize_within_stddev

from django.db.models import Count
from django.core.cache import cache
from django.apps import apps
import numpy
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_slugs
import six
from cosinnus.utils.files import image_thumbnail_url

_CosinnusPortal = None

BOOSTED_FIELD_BOOST = 1.5


# how much multiplicative boost penalty some Models get for not having an image
DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE = 0.7



class CommaSeperatedIntegerMultiValueField(indexes.MultiValueField):
    """ Custom SearchField, to use with a model's `CommaSeparatedIntegerField` """
    
    def convert(self, value):
        return ensure_list_of_ints(value)


class DefaultTagObjectIndex(indexes.SearchIndex):
    #mt_location_place = indexes.CharField(model_attr='media_tag__location_place', null=True)
    #mt_people_name = indexes.CharField(model_attr='media_tag__people_name', null=True)
    mt_public = indexes.BooleanField(model_attr='media_tag__public', null=True)


class TagObjectIndex(indexes.SearchIndex):
    mt_location = indexes.CharField(model_attr='media_tag__location', null=True)
    mt_location_lat = indexes.FloatField(model_attr='media_tag__location_lat', null=True)
    mt_location_lon = indexes.FloatField(model_attr='media_tag__location_lon', null=True)
    #mt_approach = indexes.CharField(model_attr='media_tag__approach', null=True) # approach hidden for now
    mt_topics = CommaSeperatedIntegerMultiValueField(model_attr='media_tag__topics', null=True)
    mt_visibility = indexes.IntegerField(model_attr='media_tag__visibility', null=True)


def get_tag_object_index():
    """
    Return the cosinnus tag object search index that is defined in
    :data:`settings.COSINNUS_TAG_OBJECT_SEARCH_INDEX`
    """
    from django.core.exceptions import ImproperlyConfigured
    from cosinnus.conf import settings
    
    # if the setting points at the TagObjectIndex defined here, link it directly,
    # otherwise we will get circular import problems
    if getattr(settings, 'COSINNUS_TAG_OBJECT_SEARCH_INDEX', None) == '%s.TagObjectIndex' % __name__:
        index_class = TagObjectIndex
    else:
        index_class = import_from_settings('COSINNUS_TAG_OBJECT_SEARCH_INDEX')
    
    
    if not issubclass(index_class, indexes.SearchIndex):
        raise ImproperlyConfigured("COSINNUS_TAG_OBJECT_SEARCH_INDEX refers to "
                                   "index '%s' that does not exist or is not a "
                                   "valid haystack SearchIndex." %
            settings.COSINNUS_TAG_OBJECT_SEARCH_INDEX)
    return index_class


TagObjectSearchIndex = get_tag_object_index()


class TemplateResolveMixin(object):

    def prepare_template(self, obj):
        """
        Does the same as :func:`haystack.fields.CharField.prepare_template`,
        except it replaces all occurrences of ``{app_label}``, ``{model_name}``
        and ``{field_name}`` with the respective values on the given path(s).
        """
        if self.instance_name is None and self.template_name is None:
            raise SearchFieldError("This field requires either its "
                                   "instance_name variable to be populated or "
                                   "an explicit template_name in order to "
                                   "load the correct template.")

        if self.template_name is not None:
            template_names = self.template_name
            if not isinstance(template_names, (list, tuple)):
                template_names = [template_names]
        else:
            template_names = ['search/indexes/{app_label}/{model_name}_{field_name}.txt']

        resolve_data = {
            'app_label': obj._meta.app_label,
            'model_name': obj._meta.model_name,
            'field_name': self.instance_name,
        }
        resolved_template_names = [tn.format(**resolve_data) for tn in template_names]
        t = loader.select_template(resolved_template_names)
        return t.render({'object': obj})



class TemplateResolveCharField(TemplateResolveMixin, indexes.CharField):
    pass

class TemplateResolveNgramField(TemplateResolveMixin, indexes.NgramField):
    pass


class StoredDataIndexMixin(indexes.SearchIndex):
    """ Stored field data, used when the rendered search result is not appropriate (e.g. in map search).
        Override the prepare_<field> method for different implementing Models where the field sources differ!
     """
    
    title = indexes.CharField(stored=True, indexed=False)
    # slug for linking
    slug = indexes.CharField(stored=True, indexed=True)
    url = indexes.CharField(stored=True, indexed=False)
    description = indexes.CharField(stored=True, indexed=False)
    # the small icon image, should be a 144x144 image
    icon_image_url = indexes.CharField(stored=True, indexed=False)
    # the small background image or None, should be a 500x275 image
    background_image_small_url = indexes.CharField(stored=True, indexed=False)
    # the large background image or None, should be a 1000x550 image
    background_image_large_url = indexes.CharField(stored=True, indexed=False)
    # group slug for linking, subject to implementing indexed
    group_slug = indexes.CharField(stored=True, indexed=True)
    # group name for linking, subject to implementing indexed
    group_name = indexes.CharField(stored=True, indexed=False)
    # attendees for events, projects for groups
    participant_count = indexes.IntegerField(stored=True, indexed=False)
    # member count for projects/groups, group-member count for events, memberships for users
    member_count = indexes.IntegerField(stored=True, indexed=False)
    # groups/projects: number of upcoming events
    content_count = indexes.IntegerField(stored=True, indexed=False)
    
    def prepare_participant_count(self, obj):
        """ Stub, overridden by individual indexes """
        return -1
    
    def prepare_member_count(self, obj):
        """ Stub, overridden by individual indexes """
        return -1
    
    def prepare_content_count(self, obj):
        """ Stub, overridden by individual indexes """
        return -1
    
    def prepare_group_slug(self, obj):
        """ Stub, overridden by individual indexes """
        return None
    
    def prepare_group_name(self, obj):
        """ Stub, overridden by individual indexes """
        return None
    
    def prepare_title(self, obj):
        return obj.title
    
    def prepare_slug(self, obj):
        return obj.slug
    
    def prepare_url(self, obj):
        return obj.get_absolute_url()
    
    def get_image_field_for_icon(self, obj):
        """ Stub: Overrride this and return one of:
            - an image field to be resized (preferred)
            - a string URL for a direct image that won't be resized
            - None """
        return None
    
    def get_image_field_for_background(self, obj):
        """ Stub: Overrride this and return one of:
            - an image field to be resized (preferred)
            - a string URL for a direct image that won't be resized
            - None """
        return None
    
    def prepare_icon_image_url(self, obj):
        """ This should not be overridden """
        image = self.get_image_field_for_icon(obj)
        if image and isinstance(image, six.string_types):
            return image
        return image_thumbnail_url(image, (144, 144))
    
    def prepare_background_image_small_url(self, obj):
        """ This should not be overridden """
        image = self.get_image_field_for_background(obj)
        if image and isinstance(image, six.string_types):
            return image
        return image_thumbnail_url(image, (500, 275))
    
    def prepare_background_image_large_url(self, obj):
        """ This should not be overridden """
        image = self.get_image_field_for_background(obj)
        if image and isinstance(image, six.string_types):
            return image
        return image_thumbnail_url(image, (1000, 350))
    
    def prepare_description(self, obj):
        return obj.description

class LocalCachedIndexMixin(object):
    """ If an index caches attributes locally on object instances,
        this mixin takes care of resetting them before a fresh update for that index.
        
        Define `local_cached_attrs` in the implementing class! """
    
    local_cached_attrs = []
    
    def update_object(self, instance, **kwargs):
        # remove the local cache
        for attr in self.local_cached_attrs:
            if hasattr(instance, attr):
                delattr(instance, attr)
        return super(LocalCachedIndexMixin, self).update_object(instance, **kwargs)

class DocumentBoostMixin(object):
    """ Handles standardized document boosting and exposes an index-specific
        `boost_model()` method to be implemented by each extending SearchIndex """
    
    local_boost = indexes.FloatField(default=0.0, indexed=False)
    
    def get_mean_and_stddev(self, qs_or_func, count_property, non_annotated_property=False):
        """ For a given QS or function that returns one, and the countable property
            to be annotated, return mean and stddev for the population of counts.
            Mean and Stddev are cached.
            @param non_annotated_property: If true, the given property is considered a literal number
                and will not be Count() aggregated """
        
        global _CosinnusPortal
        if _CosinnusPortal is None: 
            _CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
        portal_id = _CosinnusPortal.get_current().id
        
        INDEX_POP_COUNT_MEAN = 'cosinnus/core/portal/%d/users/%s/%s/mean' % (portal_id, self.__class__.__name__, count_property)
        INDEX_POP_COUNT_STDDEV = 'cosinnus/core/portal/%d/users/%s/%s/stddev' % (portal_id, self.__class__.__name__, count_property)
        
        mean = cache.get(INDEX_POP_COUNT_MEAN)
        stddev = cache.get(INDEX_POP_COUNT_STDDEV)
        if mean is None or stddev is None:
            # calculate mean and stddev of the counts of group memberships for active users in this portal
            qs = qs_or_func() if callable(qs_or_func) else qs_or_func
            if non_annotated_property:
                count_population = qs.values_list(count_property, flat=True)
            else:
                ann = qs.annotate(
                    pop_property_count=Count(count_property)
                )
                count_population = ann.values_list('pop_property_count', flat=True)
            mean = numpy.mean(count_population)
            stddev = numpy.std(count_population)
            cache.set(INDEX_POP_COUNT_MEAN , mean, 60*60*12)
            cache.set(INDEX_POP_COUNT_STDDEV, stddev, 60*60*12)
        return mean, stddev
    
    
    def boost_model(self, obj, indexed_data):
        """ Model specific boost for an instance given it and its indexed data.
            Stub, implement this in your SearchIndex to customize boosting for that model.
            @return: NOTE: Please normalize all return values to a range of [0.0..1.0]!
        """
        return 1.0
    
    def apply_boost_penalty(self, obj, indexed_data):
        """ Model-instance specific penalty, multiplied onto the boost calculated with `boost_model()`.
            Can be used for example to penalize contents with no preview image.
            Stub, implement this in your SearchIndex to customize boosting for that model.
            @return: 1.0 for no penalty, a float in range [0.0..1.0] for a penalty
        """
        return 1.0
        
    def prepare(self, obj):
        """ Boost all objects of this type """
        data = super(DocumentBoostMixin, self).prepare(obj)
        global_boost = getattr(settings, 'COSINNUS_HAYSTACK_GLOBAL_MODEL_BOOST_MULTIPLIERS', {}).get(data['django_ct'], 1.0)
        global_offset = getattr(settings, 'COSINNUS_HAYSTACK_GLOBAL_MODEL_BOOST_OFFSET', {}).get(data['django_ct'], 0.0)
        model_boost = self.boost_model(obj, data)
        model_boost = model_boost * self.apply_boost_penalty(obj, data)
        # this is our custom field
        data['local_boost'] = global_offset + (model_boost * global_boost)
        # this tells haystack to boost the ._score
        data['boost'] = data['local_boost']
        # TODO: remove after mokwi launch
        if False and settings.DEBUG:
            print((">> local_boost is", data['boost'], " from model*global ", model_boost, '*', \
                global_boost+1.0, data['django_ct'], getattr(obj, 'name', getattr(obj, 'title', None)), \
                getattr(obj, 'group', None) and ( 'group is: ' + obj.group.name) or ''))
        return data
    

class BaseTaggableObjectIndex(LocalCachedIndexMixin, DocumentBoostMixin, TagObjectSearchIndex):
    text = TemplateResolveNgramField(document=True, use_template=True)
    rendered = TemplateResolveCharField(use_template=True, indexed=False)
    
    boosted = indexes.NgramField(model_attr='title', boost=BOOSTED_FIELD_BOOST)

    creator = indexes.IntegerField(null=True)
    portal = indexes.IntegerField(model_attr='group__portal_id')
    group = indexes.IntegerField(model_attr='group_id')
    group_members = indexes.MultiValueField(indexed=False)
    location = indexes.LocationField(null=True)
    created = indexes.DateTimeField(model_attr='created')
    
    local_cached_attrs = ['_group_members']
    
    def prepare_creator(self, obj):
        """ Returning this without using model_attr because of a haystack bug resolving lazy objects """
        return obj.creator_id
    
    def prepare_group_slug(self, obj):
        return obj.group.slug
    
    def prepare_group_name(self, obj):
        # filter all default user groups if the new dashboard is being used (they count as "on plattform" and aren't shown)
        if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) and obj.group.slug in get_default_user_group_slugs():
            return None
        return obj.group.name
    
    def prepare_group_members(self, obj):
        if not hasattr(obj, '_group_members'):
            obj._group_members = obj.group.members
        return obj._group_members
    
    def prepare_member_count(self, obj):
        """ Group member count for taggable objects """
        return len(self.prepare_group_members(obj))
    
    def prepare_location(self, obj):
        if obj.media_tag and obj.media_tag.location_lat and obj.media_tag.location_lon:
            # this expects (lat,lon)!
            return "%s,%s" % (obj.media_tag.location_lat, obj.media_tag.location_lon)
        return None

    def prepare_description(self, obj):
        return None
    
    def get_image_field_for_icon(self, obj):
        return obj.group.get_image_field_for_icon()
    
    def index_queryset(self, using=None):
        model_cls = self.get_model()
        app_name = model_cls.__module__.split('.')[0] # eg 'cosinnus_etherpad'
        excluded_groups_for_app = [group.id for group in CosinnusGroup.objects.with_deactivated_app(app_name)]
        # TODO: check if this works properly
        qs = model_cls.objects.exclude(group__id__in=excluded_groups_for_app)
        # don't index inactive group's items
        qs = qs.filter(group__is_active=True)
        return qs.select_related('media_tag').select_related('group').all()
    
    def boost_model(self, obj, indexed_data):
        """ We boost by number of members the tagged objects's group has, normalized over
            the mean/stddev of the member count of all groups in this portal (excluded the Forum!), 
            in a range of [0.0..1.0].
            Special case: Events in the Forum always return 0.5! (Because everyone is in the Forum
            so it should be average. """
        group = obj.group
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        if group.slug == forum_slug:
            return 0.5
        
        def qs_func():
            qs = get_cosinnus_group_model().objects.all_in_portal()
            if forum_slug:
                qs = qs.exclude(slug=forum_slug)
            return qs
        
        mean, stddev = self.get_mean_and_stddev(qs_func, 'memberships')
        group_member_count = group.actual_members.count()
        members_rank = normalize_within_stddev(group_member_count, mean, stddev, stddev_factor=1.0)
        return members_rank
        
class BaseHierarchicalTaggableObjectIndex(BaseTaggableObjectIndex):
    
    def index_queryset(self, using=None):
        qs = super(BaseHierarchicalTaggableObjectIndex, self).index_queryset(using=using)
        return qs.filter(is_container=False)
