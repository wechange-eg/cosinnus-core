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

from cosinnus.models.tagged import BaseTaggableObjectModel, BaseTagObject
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.group import get_cosinnus_group_model

MODEL_ALIASES = {
    'todo': 'cosinnus_todo.todoentry',
    'file': 'cosinnus_file.fileentry',
    'etherpad': 'cosinnus_etherpad.etherpad',
    'note': 'cosinnus_note.note',
    'event': 'cosinnus_event.event',
    'user': '<userprofile>',
}


class TaggableModelSearchForm(SearchForm):
    """
    This is almost the same search form as shipped with django-haystack except
    it limits the choices to models that are a subclasses of the
    :class:`~cosinnus.models.BaseTaggableObjectModel`.
    """

    groups = forms.ChoiceField(label=_('Limit to teams'), required=False, initial='all',
        choices=(('all', _('All')), ('mine', _('My teams')), ('others', _('Other teams'))),
        widget=forms.RadioSelect)
    models = forms.MultipleChoiceField(required=False)

    location = forms.CharField(required=False)
    valid_start = forms.DateField(required=False)
    valid_end = forms.DateField(required=False)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(TaggableModelSearchForm, self).__init__(*args, **kwargs)
        self.fields['models'].choices = MODEL_ALIASES.items()

    def get_models(self):
        """ Return the models of types user has selected to filter search on """
        search_models = []

        if self.is_valid():
            for model_alias in self.cleaned_data.get('models', []):
                if model_alias in MODEL_ALIASES.keys():
                    model_string = MODEL_ALIASES[model_alias]
                    if model_string == '<userprofile>':
                        model = get_user_profile_model()
                    else:
                        model = models.get_model(*model_string.split('.'))
                    search_models.append(model)
        return search_models

    def search(self):
        sqs = super(TaggableModelSearchForm, self).search()
        if hasattr(self, 'cleaned_data'):
            sqs = self._filter_for_read_access(sqs)
            sqs = self._filter_group_selection(sqs)
            sqs = self._filter_media_tags(sqs)
        return sqs.models(*self.get_models())

    def _filter_for_read_access(self, sqs):
        """
        Given a SearchQuerySet, this function adds a filter that limits the
        result set to only include elements with read access.
        """
        public_node = (
            SQ(public__exact=True) |  # public on the object itself (applicable for groups)
            SQ(mt_visibility__exact=BaseTagObject.VISIBILITY_ALL) |  # public via "everyone can see me" visibility meta attribute
            SQ(always_visible__exact=True) # special marker for indexed objects that should always show up in search
        )

        user = self.request.user
        if user.is_authenticated():
            if check_user_superuser(user):
                pass
            else:
                users_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(user)
                logged_in_user_visibility = (
                    SQ(user_visibility_mode__exact=True) & # for UserProfile search index objects
                    SQ(mt_visibility__exact=BaseTagObject.VISIBILITY_GROUP) # logged in users can see users who are visible           
                )
                same_group_members_visibility = (
                    SQ(user_visibility_mode__exact=True) & # for UserProfile search index objects
                    SQ(mt_visibility__exact=BaseTagObject.VISIBILITY_USER) &# team mambers can see this user 
                    SQ(membership_groups__in=users_group_ids)
                )
                
                sqs = sqs.filter_and(
                    SQ(group_members__contains=user.id) |
                    public_node |
                    logged_in_user_visibility |
                    same_group_members_visibility
                )
        else:
            sqs = sqs.filter_and(public_node)
            
        return sqs


    def _filter_group_selection(self, sqs):
        """
        Checks the request for an query parameter ``groups`` which can be one of

        ``all``
            Don't filter on groups (except the respective permissions)

        ``mine``
            Only include results of groups the current user is a member of

        ``others``
            Only include results of groups the current user is not a member of

        Any other value will be interpreted as ``all``.
        """
        user = self.request.user
        if user.is_authenticated():
            term = self.cleaned_data.get('groups', 'all').lower()
            if term == 'mine':
                sqs = sqs.filter_and(group_members__contains=user.id)
            elif term == 'others':
                sqs = sqs.exclude(group_members__contains=user.id)
            else:
                pass
        # we don't need to limit the result set on anonymous user. They are not
        # a member of any group.
        return sqs

    def _filter_media_tags(self, sqs):
        location = self.cleaned_data.get('location', None)
        if location:
            sqs = sqs.filter_and(mt_location__contains=location.lower())
        start = self.cleaned_data.get('valid_start', None)
        if start:
            sqs = sqs.filter_and(mt_valid_start__gte=start)
        end = self.cleaned_data.get('valid_end', None)
        if end:
            sqs = sqs.filter_and(mt_valid_end__gte=end)
        return sqs
