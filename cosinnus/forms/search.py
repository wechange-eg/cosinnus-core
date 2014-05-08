# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.db import models
from django.utils.encoding import smart_text
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _

from haystack import connections
from haystack.backends import SQ
from haystack.constants import DEFAULT_ALIAS
from haystack.forms import SearchForm, model_choices

from cosinnus.models.tagged import BaseTaggableObjectModel


def taggable_model_choices(using=DEFAULT_ALIAS):
    """
    Returns all models sorted by their verbose_name_plural that fulfill the
    following criteria:

    1. has a valid haystack index
    2. has a haystack index is defined on the default haystack connection
    3. is not abstract
    4. inherits from :class:`~cosinnus.model.tagged.BaseTaggableObjectModel`
    """
    choices = [
        (
            "%s.%s" % (m._meta.app_label, m._meta.module_name),
            capfirst(smart_text(m._meta.verbose_name_plural))
        ) for m in filter(
            lambda m: not m._meta.abstract and issubclass(m, BaseTaggableObjectModel),
            connections[using].get_unified_index().get_indexed_models()
        )
    ]
    return sorted(choices, key=lambda x: x[1])


class TaggableModelSearchForm(SearchForm):
    """
    This is almost the same search form as shipped with django-haystack except
    it limits the choices to models that are a subclasses of the
    :class:`~cosinnus.models.BaseTaggableObjectModel`.
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(TaggableModelSearchForm, self).__init__(*args, **kwargs)
        self.fields['models'] = forms.MultipleChoiceField(
            choices=taggable_model_choices(),
            required=False,
            label=_('Search In'),
            widget=forms.CheckboxSelectMultiple
        )

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []

        if self.is_valid():
            for model in self.cleaned_data['models']:
                search_models.append(models.get_model(*model.split('.')))

        return search_models

    def search(self):
        sqs = super(TaggableModelSearchForm, self).search()
        sqs = self._filter_for_read_access(sqs)
        return sqs.models(*self.get_models())

    def _filter_for_read_access(self, sqs):
        """
        Given a SearchQuerySet, this function adds a filter that limits the
        result set to only include elements with read access.
        """

        public_node = (
            SQ(public__exact=True) |  # public on the object itself
            SQ(group_public__exact=True) |  # public group
            SQ(mt_public__exact=True)  # public via meta attribute
        )

        user = self.request.user
        if user.is_authenticated():
            if user.is_superuser:
                pass
            else:
                sqs = sqs.filter_and(
                    SQ(group_members__contains=user.id) |
                    public_node
                )
        else:
            sqs = sqs.filter_and(public_node)
        return sqs
