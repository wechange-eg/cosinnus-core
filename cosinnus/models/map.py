# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.forms.search import get_visible_portal_ids
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.models.profile import get_user_profile_model
from cosinnus.templatetags.cosinnus_tags import textfield
from copy import copy


def shorten_haystack_id(long_id):
    """ Shortens ids by replacing the <module.model> part of the id with a number. 
        Example: long_id 'cosinnus.userprofile.2' --> '3.2' """
    modulemodel, pk = long_id.rsplit('.', 1)
    short_id = '%d.%s' % (SHORTENED_ID_MAP[modulemodel], pk)
    return short_id



class BaseMapResult(dict):
    """ A single result for the search of the map, enforcing required fields """
    REQUIRED = object()
    
    fields = {
        'id': REQUIRED,
        'type': REQUIRED,
        'title': REQUIRED, 
        'slug': REQUIRED,
        'lat': None, 
        'lon': None, 
        'address': None, 
        'url': None,
        'iconImageUrl': None, 
        'backgroundImageSmallUrl': None,
        'backgroundImageLargeUrl': None,
        'description': None,
        'topics' : [], 
        'portal': None,
        'group_slug': None,
        'group_name': None,
        'participant_count': -1, # attendees for events, projects for groups
        'member_count': -1, # member count for projects/groups, group-member count for events, memberships for users
        'content_count': -1, # groups/projects: number of upcoming events
        'type': 'BaseResult', # should be different for every class
    }
    
    def __init__(self, *args, **kwargs):
        for key in self.fields.keys():
            val = kwargs.get(key, self.fields.get(key))
            if val == self.REQUIRED:
                raise Exception('MAP API Error: Expected required key "%s" for MapResult!' % key)
        return super(BaseMapResult, self).__init__(*args, **kwargs)


class HaystackMapResult(BaseMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
         
    fields = copy(BaseMapResult.fields)
    fields.update({
        'relevance': 0,
        'type': 'CompactMapResult',
    })

    def __init__(self, result, *args, **kwargs):
        if result.portals:
            # some results, like users, have multiple portals associated. we select one of those to show
            # the origin from
            visible_portals = get_visible_portal_ids()
            displayable_portals = [port_id for port_id in result.portals if port_id in visible_portals]
            current_portal_id = CosinnusPortal.get_current().id
            portal = current_portal_id if current_portal_id in displayable_portals else displayable_portals[0]
        else:
            portal = result.portal
        
        fields = {
            'id': shorten_haystack_id(result.id),
            'type': SEARCH_MODEL_NAMES[result.model],
            'title': result.title, 
            'slug': result.slug,
            'lat': result.mt_location_lat,
            'lon': result.mt_location_lon,
            'address': result.mt_location,
            'url': result.url,
            'iconImageUrl': result.icon_image_url,
            'backgroundImageSmallUrl': result.background_image_small_url,
            'backgroundImageLargeUrl': result.background_image_large_url,
            'description': textfield(result.description),
            'relevance': result.score,
            'topics': result.mt_topics,
            'portal': portal,
            'group_slug': result.group_slug,
            'group_name': result.group_name,
            'participant_count': result.participant_count,
            'member_count': result.member_count,
            'content_count': result.content_count,
        }
        fields.update(**kwargs)
        
        return super(HaystackMapResult, self).__init__(*args, **fields)
    
    
class DetailedMapResult(BaseMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, obj, *args, **kwargs):
        return super(DetailedMapResult, self).__init__(*args, **kwargs)

class DetailedUserMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, obj, *args, **kwargs):
        return super(DetailedUserMapResult, self).__init__(obj, *args, **kwargs)

class DetailedProjectMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, obj, *args, **kwargs):
        return super(DetailedProjectMapResult, self).__init__(obj, *args, **kwargs)

class DetailedSocietyMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, obj, *args, **kwargs):
        return super(DetailedSocietyMapResult, self).__init__(obj, *args, **kwargs)

class DetailedEventResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, obj, *args, **kwargs):
        return super(DetailedEventResult, self).__init__(obj, *args, **kwargs)



SHORTENED_ID_MAP = {
    'cosinnus.cosinnusproject': 1,
    'cosinnus.cosinnussociety': 2,
    'cosinnus.userprofile': 3,
    'cosinnus_event.event': 4,
}

SEARCH_MODEL_NAMES = {
    get_user_profile_model(): 'people',
    CosinnusProject: 'projects',
    CosinnusSociety: 'groups',
}
SHORT_MODEL_MAP = {
    1: CosinnusProject,
    2: CosinnusSociety,
    3: get_user_profile_model(),
}
SEARCH_RESULT_DETAIL_TYPE_MAP = {
    'people': DetailedUserMapResult,
    'projects': DetailedProjectMapResult,
    'groups': DetailedSocietyMapResult,
}
try:
    from cosinnus_event.models import Event #noqa
    SEARCH_MODEL_NAMES.update({
        Event: 'events',                           
    })
    SHORT_MODEL_MAP.update({
        4: Event,
    })
    SEARCH_RESULT_DETAIL_TYPE_MAP.update({
        'event': DetailedEventResult,
    })
except:
    Event = None

SEARCH_MODEL_NAMES_REVERSE = dict([(val, key) for key, val in SEARCH_MODEL_NAMES.items()])

