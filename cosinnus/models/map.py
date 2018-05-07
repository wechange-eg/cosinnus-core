# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy

from django.core.urlresolvers import reverse

from cosinnus.forms.search import get_visible_portal_ids
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject, \
    CosinnusGroup
from cosinnus.models.profile import get_user_profile_model
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.permissions import check_ug_membership
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.group import message_group_admins_url
from django.utils.html import escape
from django.template.defaultfilters import linebreaksbr


def _prepend_url(user, portal):
    """ Adds a signup-url with ?next= parameter to a URL for unregistered users,
        and always adds the correct portal domain """
    return portal.get_domain() + ('' if user.is_authenticated() else reverse('cosinnus:user-add') + '?join_msg=1&next=')


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
            'id': itemid_from_searchresult(result),
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
    
    
class DetailedMapResult(HaystackMapResult):
    """ Takes a Haystack Search Result and the actual Model Instance of that result and combines both of them """
    
    fields = copy(HaystackMapResult.fields)
    fields.update({
        'type': 'DetailedMapResult',
        'is_member': False,
    })
    
    background_image_field = None
    
    """
    def prepare_background_image_large_url(self, image):
        if not image:
            return None
        if image and isinstance(image, six.string_types):
            return image
        return image_thumbnail_url(image, (1000, 350))
    """
    
    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        kwargs.update({
            'morestuff': 'Moar Stuff!',
        })
        """
        if self.background_image_field:
            kwargs['backgroundImageLargeUrl'] = self.prepare_background_image_large_url(getattr(obj, self.background_image_field))
        """
        
        return super(DetailedMapResult, self).__init__(haystack_result, *args, **kwargs)


class DetailedBaseGroupMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
         
    background_image_field = 'wallpaper'

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        group_admins = list(obj.actual_admins)
        
        kwargs.update({
            'is_member': check_ug_membership(user, obj),
            'action_url_1': _prepend_url(user, obj.portal) + group_aware_reverse('cosinnus:group-microsite', kwargs={'group': obj}) + '?join=1',
            'action_url_2': _prepend_url(user, obj.portal) + message_group_admins_url(obj, group_admins),
            'youtube_url': obj.video,
            'twitter_username': obj.twitter_username,
            'flickr_url': obj.flickr_url,
            'website_url': obj.website,
            'contact': linebreaksbr(escape(obj.contact_info)),
            
        })
        """ TODO: check all read permissions on related objects! """
        
        return super(DetailedBaseGroupMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedProjectMapResult(DetailedBaseGroupMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        return super(DetailedProjectMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedSocietyMapResult(DetailedBaseGroupMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        return super(DetailedSocietyMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedUserMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
         
    # todo: show portals?

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        kwargs.update({
            'is_member': user.id == obj.user_id
        })
        return super(DetailedUserMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedEventResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        kwargs.update({
            'is_member': check_ug_membership(user, obj.group)
        })
        return super(DetailedEventResult, self).__init__(haystack_result, obj, user, *args, **kwargs)



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
        'events': DetailedEventResult,
    })
except:
    Event = None

SEARCH_MODEL_NAMES_REVERSE = dict([(val, key) for key, val in SEARCH_MODEL_NAMES.items()])
# these can always be read by any user (returned fields still vary)
SEARCH_MODEL_TYPES_ALWAYS_READ_PERMISSIONS = [
    'projects',
    'groups',
]


def itemid_from_searchresult(result):
    """ Returns a unique long id for a haystack result without revealing any DB ids. 
        itemid: <portal_id>.<modeltype>.<slug>
        Example:  `1.people.saschanarr` """
    return '%d.%s.%s' % (result.portal or 0, SEARCH_MODEL_NAMES[result.model], result.slug)


