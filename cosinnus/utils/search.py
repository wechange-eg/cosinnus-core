# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
from django.db.models.loading import get_model
import numpy
from cosinnus.utils.group import get_cosinnus_group_model

_CosinnusPortal = None

BOOSTED_FIELD_BOOST = 1.5

# global, multiplicative boost multipliers multiplied to *every* instance of
# the given models (as django contenttypes strs).
# if a model is not listed here, 1.0 is assumend
# this exists so we can blanket boost specific models for visibility without diving
# into the SearchIndexes and boost logic.
GLOBAL_MODEL_BOOST_MULTIPLIERS = {
    'cosinnus_event.event': 2.0,
} 


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
        return t.render(Context({'object': obj}))



class TemplateResolveCharField(TemplateResolveMixin, indexes.CharField):
    pass

class TemplateResolveEdgeNgramField(TemplateResolveMixin, indexes.EdgeNgramField):
    pass


class StoredDataIndexMixin(indexes.SearchIndex):
    """ Stored field data, used when the rendered search result is not appropriate (e.g. in map search).
        Override the prepare_<field> method for different implementing Models where the field sources differ!
     """
    
    title = indexes.CharField(stored=True, indexed=False)
    url = indexes.CharField(stored=True, indexed=False)
    marker_image_url = indexes.CharField(stored=True, indexed=False)
    description = indexes.CharField(stored=True, indexed=False)
    
    def prepare_title(self, obj):
        return obj.title
    
    def prepare_url(self, obj):
        return obj.get_absolute_url()
    
    def prepare_marker_image_url(self, obj):
        return None
    
    def prepare_description(self, obj):
        return obj.description


class DocumentBoostMixin(object):
    """ Handles standardized document boosting and exposes an index-specific
        `boost_model()` method to be implemented by each extending SearchIndex """
    
    local_boost = indexes.FloatField(default=0.0, indexed=False)
    
    def get_mean_and_stddev(self, qs_or_func, count_property):
        """ For a given QS or function that returns one, and the countable property
            to be annotated, return mean and stddev for the population of counts.
            Mean and Stddev are cached. """
        
        global _CosinnusPortal
        if _CosinnusPortal is None: 
            _CosinnusPortal = get_model('cosinnus', 'CosinnusPortal')
        portal_id = _CosinnusPortal.get_current().id
        
        INDEX_POP_COUNT_MEAN = 'cosinnus/core/portal/%d/users/%s/%s/mean' % (portal_id, self.__class__.__name__, count_property)
        INDEX_POP_COUNT_STDDEV = 'cosinnus/core/portal/%d/users/%s/%s/stddev' % (portal_id, self.__class__.__name__, count_property)
        
        mean = cache.get(INDEX_POP_COUNT_MEAN)
        stddev = cache.get(INDEX_POP_COUNT_STDDEV)
        if mean is None or stddev is None:
            # calculate mean and stddev of the counts of group memberships for active users in this portal
            qs = qs_or_func() if callable(qs_or_func) else qs_or_func
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
        """ 
            Model specific boost for an instance given it and its indexed data.
            Stub, implement this in your SearchIndex to customize boosting for that model.
            @return: NOTE: Please normalize all return values to a range of [0.0..1.0]!
        """
        return 1.0
        
    def prepare(self, obj):
        """ Boost all objects of this type """
        data = super(DocumentBoostMixin, self).prepare(obj)
        global_boost = GLOBAL_MODEL_BOOST_MULTIPLIERS.get(data['django_ct'], 1.0)
        model_boost = self.boost_model(obj, data)
        # this is our custom field
        data['local_boost'] = model_boost * (global_boost + 1.0)
        # this tells haystack to boost the ._score
        data['boost'] = data['local_boost']
        if settings.DEBUG:
            print ">> local_boost is", data['boost'], " from model*global ", model_boost, '*', \
                global_boost+1.0, data['django_ct'], getattr(obj, 'name', getattr(obj, 'title', None)), \
                getattr(obj, 'group', None) and ( 'group is: ' + obj.group.name) or ''
        return data
    

class BaseTaggableObjectIndex(DocumentBoostMixin, StoredDataIndexMixin, TagObjectSearchIndex):
    text = TemplateResolveEdgeNgramField(document=True, use_template=True)
    rendered = TemplateResolveCharField(use_template=True, indexed=False)
    
    boosted = indexes.EdgeNgramField(model_attr='title', boost=BOOSTED_FIELD_BOOST)

    creator = indexes.IntegerField(model_attr='creator__id', null=True)
    portal = indexes.IntegerField(model_attr='group__portal_id')
    group = indexes.IntegerField(model_attr='group_id', indexed=False)
    group_members = indexes.MultiValueField(model_attr='group__members')
    location = indexes.LocationField(null=True)

    def prepare_location(self, obj):
        if obj.media_tag and obj.media_tag.location_lat and obj.media_tag.location_lon:
            # this expects (lat,lon)!
            return "%s,%s" % (obj.media_tag.location_lat, obj.media_tag.location_lon)
        return None

    def prepare_description(self, obj):
        return None
    
    def index_queryset(self, using=None):
        model_cls = self.get_model()
        app_name = model_cls.__module__.split('.')[0] # eg 'cosinnus_etherpad'
        excluded_groups_for_app = [group.id for group in CosinnusGroup.objects.with_deactivated_app(app_name)]
        # TODO: check if this works properly
        qs = model_cls.objects.exclude(group__id__in=excluded_groups_for_app)
        # don't index inactive group's items
        qs = qs.filter(group__is_active=True)
        return qs.select_related('media_tag').all()
    
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
