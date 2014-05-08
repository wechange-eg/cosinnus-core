# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template import loader, Context

from haystack import indexes
from haystack.exceptions import SearchFieldError

from cosinnus.utils.import_utils import import_from_settings


def prepare_user(obj):
    if obj is None:
        return ''
    return obj.get_full_name() or obj.username


def prepare_users(users):
    if not users:
        return []
    return map(prepare_user, users)


class DefaultTagObjectIndex(indexes.SearchIndex):
    mt_location_place = indexes.CharField(model_attr='media_tag__location_place')
    mt_people_name = indexes.CharField(model_attr='media_tag__people_name')
    mt_public = indexes.BooleanField(model_attr='media_tag__public')


def get_tag_object_index():
    """
    Return the cosinnus tag object search index that is defined in
    :data:`settings.COSINNUS_TAG_OBJECT_SEARCH_INDEX`
    """
    from django.core.exceptions import ImproperlyConfigured
    from cosinnus.conf import settings

    index_class = import_from_settings('COSINNUS_TAG_OBJECT_SEARCH_INDEX')
    if not issubclass(index_class, indexes.SearchIndex):
        raise ImproperlyConfigured("COSINNUS_TAG_OBJECT_SEARCH_INDEX refers to "
                                   "index '%s' that does not exist or is not a "
                                   "valid haystack SearchIndex." %
            settings.COSINNUS_TAG_OBJECT_SEARCH_INDEX)
    return index_class


TagObjectSearchIndex = get_tag_object_index()


class TemplateResolveCharField(indexes.CharField):

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
            'model_name': obj._meta.module_name,
            'field_name': self.instance_name,
        }
        resolved_template_names = [tn.format(**resolve_data) for tn in template_names]
        t = loader.select_template(resolved_template_names)
        return t.render(Context({'object': obj}))


class BaseTaggableObjectIndex(TagObjectSearchIndex):
    text = TemplateResolveCharField(document=True, use_template=True)
    rendered = TemplateResolveCharField(use_template=True, indexed=False)

    title = indexes.NgramField(model_attr='title')
    slug = indexes.CharField(model_attr='slug', indexed=False)
    creator = indexes.CharField(model_attr='creator')
    created = indexes.DateTimeField(model_attr='created')

    group = indexes.IntegerField(model_attr='group_id', indexed=False)
    group_name = indexes.CharField(model_attr='group__name')
    group_slug = indexes.CharField(model_attr='group__slug', indexed=False)
    group_public = indexes.BooleanField(model_attr='group__public')
    group_members = indexes.MultiValueField(model_attr='group__members')

    def index_queryset(self, using=None):
        return self.get_model().objects.select_related('media_tag').all()

    def prepare_creator(self, obj):
        return prepare_user(obj.creator)
