# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.apps import apps
from django.utils.encoding import smart_text
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _

from haystack import connections
from haystack.backends import SQ
from haystack.constants import DEFAULT_ALIAS
from haystack.forms import SearchForm, model_choices

from cosinnus.conf import settings
from cosinnus.models.tagged import BaseTaggableObjectModel, BaseTagObject
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.group import get_cosinnus_group_model
from haystack.inputs import AutoQuery
from cosinnus.forms.select2 import CommaSeparatedSelect2MultipleChoiceField,\
    CommaSeparatedSelect2MultipleWidget
from haystack.query import EmptySearchQuerySet
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.functions import ensure_list_of_ints

MODEL_ALIASES = {
    'todo': 'cosinnus_todo.todoentry',
    'file': 'cosinnus_file.fileentry',
    'etherpad': 'cosinnus_etherpad.etherpad',
    'ethercalc': 'cosinnus_etherpad.ethercalc',
    'note': 'cosinnus_note.note',
    'event': 'cosinnus_event.event',
    'user': '<userprofile>',
    'poll': 'cosinnus_poll.Poll',
    'offer': 'cosinnus_marketplace.Offer',
    'project': 'cosinnus.CosinnusProject',
    'group': 'cosinnus.CosinnusSociety',
}

VISIBLE_PORTAL_IDS = None  # global

def filter_searchqueryset_for_read_access(sqs, user):
    """
    Given a SearchQuerySet, this function adds a filter that limits the
    result set to only include elements with read access.
    """
    public_node = (
        SQ(public__exact=True) |  # public on the object itself (applicable for groups)
        SQ(mt_visibility__exact=BaseTagObject.VISIBILITY_ALL) |  # public via "everyone can see me" visibility meta attribute
        SQ(always_visible__exact=True) # special marker for indexed objects that should always show up in search
    )

    if user.is_authenticated:
        if check_user_superuser(user):
            pass
        else:
            logged_in_user_visibility = (
                SQ(user_visibility_mode__exact=True) & # for UserProfile search index objects
                SQ(mt_visibility__exact=BaseTagObject.VISIBILITY_GROUP) # logged in users can see users who are visible           
            )
            my_item = (
                 SQ(creator__exact=user.id)
            )
            visible_for_all_authenticated_users = (
                SQ(visible_for_all_authenticated_users=True)
            )
            # FIXME: known problem: ``group_members`` is a stale indexed representation of the members
            # of an items group. New members of a group won't be able to find old indexed items if the index
            # is not refreshed regularly
            group_visible_and_in_my_group = (
                 SQ(mt_visibility__exact=BaseTagObject.VISIBILITY_GROUP) &
                 SQ(group_members__contains=user.id)
            )
            
            ored_query = public_node | group_visible_and_in_my_group | my_item \
                 | logged_in_user_visibility | visible_for_all_authenticated_users
            
            users_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(user)
            if users_group_ids:
                group_member_user_visibility = (
                    SQ(user_visibility_mode__exact=True) & # for UserProfile search index objects
                    SQ(mt_visibility__exact=BaseTagObject.VISIBILITY_USER) & # team mambers can see this user 
                    SQ(membership_groups__in=users_group_ids)
                )
                ored_query = ored_query | group_member_user_visibility
            
            sqs = sqs.filter_and(ored_query)
    else:
        sqs = sqs.filter_and(public_node)
        
    return sqs

def get_visible_portal_ids():
    global VISIBLE_PORTAL_IDS
    if VISIBLE_PORTAL_IDS is None:
        current_portal = CosinnusPortal.get_current().id
        portals = [current_portal] + getattr(settings, 'COSINNUS_SEARCH_DISPLAY_FOREIGN_PORTALS', [])
        VISIBLE_PORTAL_IDS = list(set(portals))
    return VISIBLE_PORTAL_IDS

def filter_searchqueryset_for_portal(sqs, portals=None, restrict_multiportals_to_current=False):
    """ Filters a searchqueryset by which portal the objects belong to.
        @param portals: If not provided, will default to this portal and all foreign portals allowed in settings 
            ([current-portal] + settings.COSINNUS_SEARCH_DISPLAY_FOREIGN_PORTALS)
        @param restrict_multiportals_to_current: if True, will force objects with multiple portals to
            definitely be in the current portal  """
            
    if portals is None:
        portals = get_visible_portal_ids()
    
    if portals and restrict_multiportals_to_current:
        sqs = sqs.filter_and(SQ(portal__in=portals) | SQ(portals__in=[CosinnusPortal.get_current().id]))
    elif portals:
        sqs = sqs.filter_and(SQ(portal__in=portals) | SQ(portals__in=portals))
    return sqs


class TaggableModelSearchForm(SearchForm):
    """
    This is almost the same search form as shipped with django-haystack except
    it limits the choices to models that are a subclasses of the
    :class:`~cosinnus.models.BaseTaggableObjectModel`.
    """
    
    MAX_RESULTS = 200

    groups = forms.ChoiceField(label=_('Limit to teams'), required=False, initial='all',
        choices=(('all', _('All')), ('mine', _('My teams')), ('others', _('Other teams'))),
        widget=forms.RadioSelect)
    models = forms.MultipleChoiceField(required=False)
    topics = CommaSeparatedSelect2MultipleChoiceField(required=False, choices=BaseTagObject.TOPIC_CHOICES,
            widget=CommaSeparatedSelect2MultipleWidget(select2_options={'closeOnSelect': 'true'}))

    location = forms.CharField(required=False)
    valid_start = forms.DateField(required=False)
    valid_end = forms.DateField(required=False)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(TaggableModelSearchForm, self).__init__(*args, **kwargs)
        self.fields['models'].choices = list(MODEL_ALIASES.items())

    def get_models(self):
        """ Return the models of types user has selected to filter search on """
        search_models = []

        if self.is_valid():
            # we either use the models given to us from the form, or if empty,
            # all models available for search
            model_aliases_query = self.cleaned_data.get('models', [])
            if not model_aliases_query:
                model_aliases_query = list(MODEL_ALIASES.keys())
            for model_alias in model_aliases_query:
                if model_alias in list(MODEL_ALIASES.keys()):
                    model_string = MODEL_ALIASES[model_alias]
                    if model_string == '<userprofile>':
                        model = get_user_profile_model()
                    else:
                        model = apps.get_model(*model_string.split('.'))
                    search_models.append(model)
        
        return search_models

    def search(self):
        sqs = super(TaggableModelSearchForm, self).search()
        
        if hasattr(self, 'cleaned_data'):
            sqs = filter_searchqueryset_for_read_access(sqs, self.request.user)
            sqs = filter_searchqueryset_for_portal(sqs)
            sqs = self._filter_group_selection(sqs)
            sqs = self._filter_media_tags(sqs)
            if self.cleaned_data.get('q', None):
                sqs = self._boost_search_query(sqs)
            if self.request.GET.get('o', None) == 'newest':
                sqs = sqs.order_by('-created', '-_score')
        ret = sqs.models(*self.get_models())
        ret = ret[:self.MAX_RESULTS]
        return ret
    
    def no_query_found(self):
        """ Overriding default behaviour to allow topic searches without textual query. """
        if hasattr(self, 'cleaned_data') and self.cleaned_data.get('topics', None):
            return self.searchqueryset.all()
        return EmptySearchQuerySet()

    def _boost_search_query(self, sqs):
        q = self.cleaned_data['q']
        sqs = sqs.filter(SQ(boosted=AutoQuery(q)) | SQ(text=AutoQuery(q)))
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
        if user.is_authenticated:
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
        topics = ensure_list_of_ints(self.cleaned_data.get('topics', []))
        if topics:
            sqs = sqs.filter_and(mt_topics__in=topics)
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
