# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy
import datetime
import json
import re
import pytz

from django.urls import reverse
from django.db.models import Q
from django.template.defaultfilters import linebreaksbr
from django.template.defaultfilters import date as django_date_filter
from django.utils.html import escape
from django.utils import timezone
from django.utils.timezone import now, is_naive
from django.template.loader import render_to_string
from haystack.query import SearchQuerySet

from cosinnus.conf import settings
from cosinnus.forms.search import get_visible_portal_ids, \
    filter_searchqueryset_for_read_access
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject,\
    CosinnusConference
from cosinnus.models.profile import get_user_profile_model
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.group import message_group_admins_url
from cosinnus.utils.permissions import check_ug_membership, check_ug_pending, \
    check_ug_invited_pending, check_user_superuser
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_event.models import Event
from cosinnus_exchange.models import ExchangeProject, ExchangeSociety, ExchangeOrganization, ExchangeEvent,\
    ExchangeConference
from cosinnus.utils.dates import HumanizedEventTimeObject
from cosinnus_organization.models import CosinnusOrganization


def _prepend_url(user, portal=None):
    """ Adds a signup-url with ?next= parameter to a URL for unregistered users,
        and always adds the correct portal domain """
    return (portal.get_domain() if portal else '') + ('' if user.is_authenticated else reverse('cosinnus:user-add') + '?join_msg=1&next=')

REQUIRED = object()

class DictResult(dict):
    """ Dictionary result object """
    
    fields = {}
    
    def __init__(self, *args, **kwargs):
        for key in list(self.fields.keys()):
            val = kwargs.get(key, self.fields.get(key))
            if val is REQUIRED:
                raise Exception('MAP API Error: Expected required key "%s" for MapResult!' % key)
        return super(DictResult, self).__init__(*args, **kwargs)

class BaseMapCard(DictResult):
    """ A single card for additional info for an object, like administrating users, subprojects, etc """
    
    fields = {
        'id': REQUIRED,
        'type': REQUIRED,
        'title': REQUIRED, 
        'slug': REQUIRED,
        'portal': None,
        'address': None, 
        'url': None,
        'iconImageUrl': None,
        'dataSlot1': None, # these are different based on the result type, usually displayed next to an icon
        'dataSlot2': None, # these are different based on the result type, usually displayed next to an icon
    }
    
    

class HaystackMapCard(BaseMapCard):
    """ Serialization class for small item cards on
        detailed search results. For example, a list of admins
        for a project on that project's detail view would
        be modeled as a `HaystackUserMapCard` """
    
    def __init__(self, result, *args, **kwargs):
        if result.portals:
            # some results, like users, have multiple portals associated. we select one of those to show
            # the origin from
            visible_portals = get_visible_portal_ids()
            displayable_portals = [port_id for port_id in result.portals if port_id in visible_portals]
            current_portal_id = CosinnusPortal.get_current().id
            portal = current_portal_id if ((current_portal_id in displayable_portals) or not displayable_portals) else displayable_portals[0]
        else:
            portal = result.portal
            
        fields = {
            'id': itemid_from_searchresult(result),
            'type': SEARCH_MODEL_NAMES[result.model],
            'title': result.title, 
            'slug': result.slug,
            'portal': portal,
            'address': result.mt_location,
            'url': result.url,
            'iconImageUrl': result.icon_image_url,

        }
        fields.update(**kwargs)
        
        return super(HaystackMapCard, self).__init__(*args, **fields)
    
    
class HaystackUserMapCard(HaystackMapCard):
    
    def __init__(self, result, *args, **kwargs):
        kwargs.update({
            'dataSlot1': None,
            'dataSlot2': None,
        })
        return super(HaystackUserMapCard, self).__init__(result, *args, **kwargs)
    
    
class HaystackProjectMapCard(HaystackMapCard):
    
    def __init__(self, result, *args, **kwargs):
        kwargs.update({
            'dataSlot1': result.member_count, # project member count
            'dataSlot2': None,
        })
        return super(HaystackProjectMapCard, self).__init__(result, *args, **kwargs)
    
    
class HaystackGroupMapCard(HaystackMapCard):
    
    def __init__(self, result, *args, **kwargs):
        kwargs.update({
            'dataSlot1': result.member_count, # group member count
            'dataSlot2': result.participant_count, # subproject count
        })
        return super(HaystackGroupMapCard, self).__init__(result, *args, **kwargs)


class HaystackConferenceMapCard(HaystackMapCard):
    
    def __init__(self, result, *args, **kwargs):
        humanized_datetime_obj = HumanizedEventTimeObject(result.from_date, result.to_date)
        kwargs.update({
            'dataSlot1': humanized_datetime_obj.get_humanized_event_time_html(), # time and date in a user-localized version
            'dataSlot2': result.participant_count, # group member count
        })
        return super(HaystackConferenceMapCard, self).__init__(result, *args, **kwargs)


class HaystackOrganizationMapCard(HaystackMapCard):
    
    def __init__(self, result, *args, **kwargs):
        return super(HaystackOrganizationMapCard, self).__init__(result, *args, **kwargs)
    
    
class HaystackEventMapCard(HaystackMapCard):
    
    def __init__(self, result, *args, **kwargs):
        humanized_datetime_obj = HumanizedEventTimeObject(result.from_date, result.to_date)
        kwargs.update({
            'dataSlot1': humanized_datetime_obj.get_humanized_event_time_html(), # time and date in a user-localized version
            'dataSlot2': None,
        })
        return super(HaystackEventMapCard, self).__init__(result, *args, **kwargs)
    

class BaseMapResult(DictResult):
    """ A single result for the search of the map, enforcing required fields """
    
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
        'text_topics': [],
        'portal': None,
        'group_slug': None,
        'group_name': None,
        'participant_count': -1,  # attendees for events, projects for groups
        'member_count': -1,  # member count for projects/groups, group-member count for events, memberships for users
        'content_count': -1,  # groups/projects: number of upcoming events
        'type': 'BaseResult',  # should be different for every class
        'liked': False,  # has the current user liked this?
        'source': None,  # source platform if external content
        'dynamic_fields': None,
        'is_open_for_cooperation': None,
    }


class HaystackMapResult(BaseMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
         
    fields = copy(BaseMapResult.fields)
    fields.update({
        'relevance': 0,
        'type': 'CompactMapResult',
    })
    if settings.COSINNUS_ENABLE_SDGS:
        fields.update({
            'sdgs': [],
        })
    if settings.COSINNUS_MANAGED_TAGS_ENABLED:
        fields.update({
            'managed_tags': [],
        })

    def __init__(self, result, user=None, *args, **kwargs):
        if result.portals:
            # some results, like users, have multiple portals associated. we select one of those to show
            # the origin from
            visible_portals = get_visible_portal_ids()
            displayable_portals = [port_id for port_id in result.portals if port_id in visible_portals]
            current_portal_id = CosinnusPortal.get_current().id
            portal = current_portal_id if ((not displayable_portals) or current_portal_id in displayable_portals) else displayable_portals[0]
        else:
            portal = result.portal
        
        if result.portal == settings.COSINNUS_EXCHANGE_PORTAL_ID:
            model_name = EXCHANGE_SEARCH_MODEL_NAMES[result.model]
        else:  
            model_name = SEARCH_MODEL_NAMES[result.model]
        fields = {
            'id': itemid_from_searchresult(result),
            'type': model_name,
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
            'text_topics': result.mt_text_topics,
            'portal': portal,
            'group_slug': result.group_slug,
            'group_name': result.group_name,
            'participant_count': result.participant_count,
            'member_count': result.member_count,
            'content_count': result.content_count,
            'liked': user.id in result.liked_user_ids if (user and getattr(result, 'liked_user_ids', [])) else False,
            'source': result.source,
            'dynamic_fields': result.dynamic_fields,
            'is_open_for_cooperation': result.is_open_for_cooperation,
        }
        if getattr(result, 'from_date', None) and getattr(result, 'to_date', None):
            humanized_datetime_obj = HumanizedEventTimeObject(result.from_date, result.to_date)
            kwargs.update({
                'time_html': humanized_datetime_obj.get_humanized_event_time_html(),
            })
        if settings.COSINNUS_ENABLE_SDGS:
            fields.update({
                'sdgs': result.sdgs,
            })
        if settings.COSINNUS_MANAGED_TAGS_ENABLED:
            fields.update({
                'managed_tags': result.managed_tags,
            })
        if 'request' in kwargs:
            kwargs.pop('request')
        fields.update(**kwargs)
        
        return super(HaystackMapResult, self).__init__(*args, **fields)
    
    
class DetailedMapResult(HaystackMapResult):
    """ Takes a Haystack Search Result and the actual Model Instance of that result and combines both of them """
    
    fields = copy(HaystackMapResult.fields)
    fields.update({
        'type': 'DetailedMapResult',
        'is_member': False,
        'is_invited': False,
        'is_pending': False,
        'report_model': None,
        'report_id': None,
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
        # collect '<app_label>.<model_name>' and id for the Feedback report popup
        app_label = obj.__class__.__module__.split('.')[0]
        model_name = obj.__class__.__name__
        model_str = '%s.%s' % (app_label, model_name)
        kwargs.update({
            'report_model': model_str,
            'report_id': obj.id,
        })
        """
        if self.background_image_field:
            kwargs['backgroundImageLargeUrl'] = self.prepare_background_image_large_url(getattr(obj, self.background_image_field))
        """
        
        return super(DetailedMapResult, self).__init__(haystack_result, user=user, *args, **kwargs)


class DetailedBaseGroupMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
         
    fields = copy(DetailedMapResult.fields)
    fields.update({
        'events': [],
        'admins': [],
        'organizations': [],
        'followed': False,
        'starred': False
    })
         
    background_image_field = 'wallpaper'

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        message_url = None
        if not settings.COSINNUS_IS_INTEGRATED_PORTAL and not 'cosinnus_message' in settings.COSINNUS_DISABLED_COSINNUS_APPS:
            if settings.COSINNUS_ROCKET_ENABLED:
                message_url = reverse('cosinnus:message-write-group', kwargs={'slug': obj.slug})
            else:
                group_admins = list(obj.actual_admins)
                message_url = message_group_admins_url(obj, group_admins)

        kwargs.update({
            'is_member': check_ug_membership(user, obj),
            'is_pending': check_ug_pending(user, obj),
            'is_invited': check_ug_invited_pending(user, obj),
            'action_url_1': _prepend_url(user, obj.portal) + group_aware_reverse('cosinnus:group-microsite', kwargs={'group': obj}, skip_domain=True) + '?join=1',
            'action_url_2': (_prepend_url(user, obj.portal) + message_url) if message_url else None,
            'youtube_url': obj.video,
            'twitter_username': obj.twitter_username,
            'flickr_url': obj.flickr_url,
            'website_url': obj.website,
            'contact': linebreaksbr(escape(obj.contact_info)),
            'followed': obj.is_user_following(user),
            'starred': obj.is_user_starring(user),
            'created': django_date_filter(obj.created, "SHORT_DATE_FORMAT"),
            'last_modified': django_date_filter(obj.last_modified, "SHORT_DATE_FORMAT"),
        })
        """ TODO: check all read permissions on related objects! """
        
        # collect upcoming and visible project/group events
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['events'])
        sqs = sqs.filter_and(group=obj.id)
        sqs = filter_searchqueryset_for_read_access(sqs, user)
        sqs = filter_event_searchqueryset_by_upcoming(sqs)
        sqs = sqs.order_by('from_date')
        kwargs.update({
            'events': [HaystackEventMapCard(result) for result in sqs]
        })
        
        # collect administrator users. these are *not* filtered by visibility, as project admins are always visible!
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['people'])
        sqs = sqs.filter_and(admin_groups=obj.id)
        #sqs = filter_searchqueryset_for_read_access(sqs, user)
        sqs = sqs.order_by('title')
        
        # private users are not visible to anonymous users, BUT they are visible to logged in users!
        # because if a user chose to make his group visible, he has to take authorship responsibilities
        if not user.is_authenticated:
            sqs = filter_searchqueryset_for_read_access(sqs, user)
            
        kwargs.update({
            'admins': [HaystackUserMapCard(result) for result in sqs]
        })
        
        if settings.COSINNUS_ORGANIZATIONS_ENABLED:
            sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['organizations'])
            sqs = sqs.filter_and(groups=obj.id)
            sqs = filter_searchqueryset_for_read_access(sqs, user)
            sqs = sqs.order_by('title')
            
            kwargs.update({
                'organizations': [HaystackOrganizationMapCard(result) for result in sqs]
            })
        
        return super(DetailedBaseGroupMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedProjectMapResult(DetailedBaseGroupMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        return super(DetailedProjectMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedSocietyMapResult(DetailedBaseGroupMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
    
    fields = copy(DetailedBaseGroupMapResult.fields)
    fields.update({
        'projects': [],
    })
    
    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        # collect group's visible projects
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['projects'])
        sqs = sqs.filter_and(id__in=obj.groups.all().values_list('id', flat=True))
        # the preview for projects and groups is always visible for everyone!
        #sqs = filter_searchqueryset_for_read_access(sqs, user)
        sqs = sqs.order_by('title')
        kwargs.update({
            'projects': [HaystackProjectMapCard(result) for result in sqs]
        })
        return super(DetailedSocietyMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedConferenceMapResult(DetailedBaseGroupMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        humanized_datetime_obj = HumanizedEventTimeObject(haystack_result.from_date, haystack_result.to_date)
        kwargs.update({
            'time_html': humanized_datetime_obj.get_humanized_event_time_html(), # time and date in a user-localized version
            'participants_limit_count': haystack_result.participants_limit_count,
        })
        return super(DetailedConferenceMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedUserMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
         
    fields = copy(DetailedMapResult.fields)
    fields.update({
        'projects': [],
        'groups': [],
        'extra_html': ''
    })

    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        kwargs.update({
            'is_member': user.id == obj.user_id,
        })
        if not settings.COSINNUS_IS_INTEGRATED_PORTAL and not 'cosinnus_message' in settings.COSINNUS_DISABLED_COSINNUS_APPS:
            if settings.COSINNUS_ROCKET_ENABLED:
                kwargs.update({
                    'action_url_1': _prepend_url(user, None) + reverse('cosinnus:message-write',
                                                                       kwargs={'username': obj.user.username}),
                })
            else:
                kwargs.update({
                    'action_url_1': _prepend_url(user, None) + reverse('postman:write',
                                                                       kwargs={'recipients': obj.user.username}),
                })
        # collect visible groups and projects that this user is in
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['projects'], SEARCH_MODEL_NAMES_REVERSE['groups'])
        sqs = sqs.filter_and(id__in=haystack_result.membership_groups)
        # the preview for projects and groups is always visible for everyone!
        #sqs = filter_searchqueryset_for_read_access(sqs, user)
        sqs = sqs.order_by('title')
        
        # render the user's media tags
        extra_html = obj.get_media_tag_fields_rendered() + '\n'
        # render the user's dynamic profile fields
        if settings.COSINNUS_USERPROFILE_EXTRA_FIELDS_SHOW_ON_MAP:
            extra_html += obj.get_dynamic_fields_rendered()
             
        kwargs.update({
            'projects': [],
            'groups': [],
            'extra_html': extra_html,
        })
        for result in sqs:
            if SEARCH_MODEL_NAMES[result.model] == 'projects':
                kwargs['projects'].append(HaystackProjectMapCard(result))
            elif SEARCH_MODEL_NAMES[result.model] == 'conferences':
                kwargs['conferences'].append(HaystackConferenceMapCard(result))
            else:
                kwargs['groups'].append(HaystackGroupMapCard(result))

        if getattr(settings, 'COSINNUS_USER_SHOW_MAY_BE_CONTACTED_FIELD', False):
            kwargs.update({
                'may_be_contacted': obj.may_be_contacted,
            })
        if obj.user_id == user.id:
            kwargs.update({
                'is_self': True,
            })
        return super(DetailedUserMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedEventResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
    
    fields = copy(DetailedMapResult.fields)
    fields.update({
        'participants': [],
        'participant_count': 0,
        'followed': False,
        'starred': False
    })
    
    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        humanized_datetime_obj = HumanizedEventTimeObject(haystack_result.from_date, haystack_result.to_date)
        kwargs.update({
            'is_member': check_ug_membership(user, obj.group),
            'time_html': humanized_datetime_obj.get_humanized_event_time_html(),
        })
        
        # collect visible attending users
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['people'])
        sqs = sqs.filter_and(user_id__in=haystack_result.participants)
        sqs = filter_searchqueryset_for_read_access(sqs, user)
        sqs = sqs.order_by('title')
        kwargs.update({
            'participants': [HaystackUserMapCard(result) for result in sqs],
            'participant_count': haystack_result.participant_count,
            'followed': obj.is_user_following(user),
            'starred': obj.is_user_starring(user)
        })
        return super(DetailedEventResult, self).__init__(haystack_result, obj, user, *args, **kwargs)


class DetailedIdeaMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
    
    fields = copy(DetailedMapResult.fields)
    fields.update({
        'projects': [],
        'followed': False,
        'starred': False
    })
    
    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        # collect group's created visible projects
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['projects'])
        sqs = sqs.filter_and(id__in=obj.created_groups.all().values_list('id', flat=True))
        # the preview for projects and groups is always visible for everyone!
        #sqs = filter_searchqueryset_for_read_access(sqs, user)
        sqs = sqs.order_by('title')
        
        kwargs.update({
            'projects': [HaystackProjectMapCard(result) for result in sqs],
            'action_url_1': _prepend_url(user, obj.portal) + reverse('cosinnus:group-add') + ('?idea=%s&name=%s' % (itemid_from_searchresult(haystack_result), escape(haystack_result.title))),
            'creator_name': obj.creator.get_full_name(),
            'creator_slug': obj.creator.username,
            'followed': obj.is_user_following(user),
            'starred': obj.is_user_starring(user),
            'created': django_date_filter(obj.created, "SHORT_DATE_FORMAT"),
            'last_modified': django_date_filter(obj.last_modified, "SHORT_DATE_FORMAT"),
        })
        ret = super(DetailedIdeaMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)
        return ret


class DetailedOrganizationMapResult(DetailedMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """
    
    fields = copy(DetailedMapResult.fields)
    fields.update({
        'projects': [],
        'groups': [],
        'admins': [],
    })
    
    def __init__(self, haystack_result, obj, user, *args, **kwargs):
        kwargs.update({
            'is_superuser': check_user_superuser(user),
            'is_member': check_ug_membership(user, obj),
            'is_pending': check_ug_pending(user, obj),
            'is_invited': check_ug_invited_pending(user, obj),
            'creator_name': obj.creator and obj.creator.get_full_name(),
            'creator_slug': obj.creator and obj.creator.username,
            'title': obj.name,
            'organization_type': obj.get_type(),
            'website_url': obj.website,
            'email': obj.email,
            'phone_number': obj.phone_number.as_international if obj.phone_number else None,
            'social_media': [{'url': sm.url, 'icon': sm.icon} for sm in obj.social_media.all()],
            'edit_url': obj.get_edit_url(),
            'accept_url': reverse('cosinnus:organization-user-accept', kwargs={'organization': obj.slug}),
        })

        # collect administrator users. these are *not* filtered by visibility, as project admins are always visible!
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['people'])
        sqs = sqs.filter_and(admin_organizations=obj.id)
        #sqs = filter_searchqueryset_for_read_access(sqs, user)
        # private users are not visible to anonymous users, BUT they are visible to logged in users!
        # because if a user chose to make his group visible, he has to take authorship responsibilities
        if not user.is_authenticated:
            sqs = filter_searchqueryset_for_read_access(sqs, user)
        kwargs.update({
            'admins': [HaystackUserMapCard(result) for result in sqs]
        })

        # Groups
        sqs = SearchQuerySet().models(SEARCH_MODEL_NAMES_REVERSE['projects'], SEARCH_MODEL_NAMES_REVERSE['groups'])
        sqs = sqs.filter_and(id__in=haystack_result.groups)
        sqs = filter_searchqueryset_for_read_access(sqs, user)
        sqs = sqs.order_by('title')
        kwargs.update({
            'groups': [HaystackGroupMapCard(result) for result in sqs]
        })
        
        super(DetailedOrganizationMapResult, self).__init__(haystack_result, obj, user, *args, **kwargs)



class CloudfileMapCard(BaseMapCard):
    fields = BaseMapCard.fields.copy()
    fields.update({
        "mtime": None,
        "mime": None,
        "size": None,
        "excerpt": None,
    })

    def __init__(self, document, query, *args, **kwargs):

        query_regexp = "|".join(re.escape(word) for word in query.split())

        try:
            excerpt = escape(document['excerpts'][0]['excerpt'])
        except LookupError:
            excerpt = None
        else:
            excerpt = re.sub(query_regexp, r"<b>\g<0></b>", excerpt, flags=re.IGNORECASE)


        super().__init__(
            id=document['id'],
            type="cloudfile",
            slug=f"{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}{document['link']}",
            title=re.sub(query_regexp, r"<b>\g<0></b>", escape(document['title']), flags=re.IGNORECASE),
            mime=document['info']['mime'],
            size=document['info']['size'],
            mtime=document['info']['mtime'],
            excerpt=excerpt,
            **kwargs
        )

SHORTENED_ID_MAP = {
    'cosinnus.cosinnusproject': 1,
    'cosinnus.cosinnussociety': 2,
    'cosinnus.userprofile': 3,
    'cosinnus_event.event': 4,
    'cosinnus.cosinnusidea': 5,
    'cosinnus_organization.cosinnusorganization': 6,
}

SEARCH_MODEL_NAMES = {
    get_user_profile_model(): 'people',
    CosinnusProject: 'projects',
    CosinnusSociety: 'groups',
    Event: 'events',
    CosinnusOrganization: 'organizations',
}

SHORT_MODEL_MAP = {
    1: CosinnusProject,
    2: CosinnusSociety,
    3: get_user_profile_model(),
    # 4: Event,
    # 5: CosinnusIdea,
    6: CosinnusOrganization,
}
SEARCH_RESULT_DETAIL_TYPE_MAP = {
    'people': DetailedUserMapResult,
    'projects': DetailedProjectMapResult,
    'groups': DetailedSocietyMapResult,
    'organizations': DetailedOrganizationMapResult,
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
    
if settings.COSINNUS_IDEAS_ENABLED:
    from cosinnus.models.idea import CosinnusIdea
    SEARCH_MODEL_NAMES.update({
        CosinnusIdea: 'ideas',                       
    })
    SHORT_MODEL_MAP.update({
        5: CosinnusIdea,
    })
    SEARCH_RESULT_DETAIL_TYPE_MAP.update({
        'ideas': DetailedIdeaMapResult,
    })
    
""" pads, files, messages, todos, polls """
try:
    from cosinnus_etherpad.models import Etherpad #noqa
    SEARCH_MODEL_NAMES.update({
        Etherpad: 'pads',                           
    })
    SHORT_MODEL_MAP.update({
        6: Etherpad,
    })
    #SEARCH_RESULT_DETAIL_TYPE_MAP.update({
    #    'pads': NYI,
    #})
except:
    Etherpad = None

try:
    from cosinnus_file.models import FileEntry #noqa
    SEARCH_MODEL_NAMES.update({
        FileEntry: 'files',                           
    })
    SHORT_MODEL_MAP.update({
        7: FileEntry,
    })
    #SEARCH_RESULT_DETAIL_TYPE_MAP.update({
    #    'pads': NYI,
    #})
except:
    FileEntry = None

if not settings.COSINNUS_ROCKET_ENABLED and not 'cosinnus_message' in settings.COSINNUS_DISABLED_COSINNUS_APPS:
    try:
        from postman.models import Message #noqa
        SEARCH_MODEL_NAMES.update({
            Message: 'messages',
        })
        SHORT_MODEL_MAP.update({
            8: Message,
        })
        #SEARCH_RESULT_DETAIL_TYPE_MAP.update({
        #    'messages': NYI,
        #})
    except:
        Message = None

try:
    from cosinnus_todo.models import TodoEntry #noqa
    SEARCH_MODEL_NAMES.update({
        TodoEntry: 'todos',                           
    })
    SHORT_MODEL_MAP.update({
        9: TodoEntry,
    })
    #SEARCH_RESULT_DETAIL_TYPE_MAP.update({
    #    'todos': NYI,
    #})
except:
    TodoEntry = None

try:
    from cosinnus_poll.models import Poll #noqa
    SEARCH_MODEL_NAMES.update({
        Poll: 'polls',                           
    })
    SHORT_MODEL_MAP.update({
        10: Poll,
    })
    #SEARCH_RESULT_DETAIL_TYPE_MAP.update({
    #    'polls': NYI,
    #})
except:
    Poll = None
    

try:
    from cosinnus_note.models import Note #noqa
    SEARCH_MODEL_NAMES.update({
        Note: 'notes',                           
    })
    SHORT_MODEL_MAP.update({
        11: Note,
    })
    #SEARCH_RESULT_DETAIL_TYPE_MAP.update({
    #    'notes': NYI,
    #})
except:
    Note = None
    

try:
    from cosinnus_marketplace.models import Offer #noqa
    SEARCH_MODEL_NAMES.update({
        Offer: 'offers',                           
    })
    SHORT_MODEL_MAP.update({
        12: Offer,
    })
    #SEARCH_RESULT_DETAIL_TYPE_MAP.update({
    #    'notes': NYI,
    #})
except:
    Offer = None


if settings.COSINNUS_ORGANIZATIONS_ENABLED:
    from cosinnus_organization.models import CosinnusOrganization
    SEARCH_MODEL_NAMES.update({
        CosinnusOrganization: 'organizations',                       
    })
    SHORT_MODEL_MAP.update({
        13: CosinnusOrganization,
    })
    SEARCH_RESULT_DETAIL_TYPE_MAP.update({
        'organizations': DetailedOrganizationMapResult,
    })

if settings.COSINNUS_CONFERENCES_ENABLED:
    SEARCH_MODEL_NAMES.update({
        CosinnusConference: 'conferences',                       
    })
    SHORT_MODEL_MAP.update({
        13: CosinnusConference,
    })
    SEARCH_RESULT_DETAIL_TYPE_MAP.update({
        'conferences': DetailedConferenceMapResult,
    })


# these can always be read by any user (returned fields still vary)
SEARCH_MODEL_TYPES_ALWAYS_READ_PERMISSIONS = [
    'projects',
    'groups',
    'conferences',
]

EXCHANGE_SEARCH_MODEL_NAMES = {
    ExchangeProject: 'projects',
    ExchangeSociety: 'groups',
    ExchangeConference: 'conferences',
    ExchangeOrganization: 'organizations',
    ExchangeEvent: 'events'
}
    
SHORTENED_ID_MAP_REVERSE = dict([(val, key) for key, val in list(SHORTENED_ID_MAP.items())])
SEARCH_MODEL_NAMES_REVERSE = dict([(val, key) for key, val in list(SEARCH_MODEL_NAMES.items())])
SHORT_MODEL_MAP_REVERSE = dict([(val, key) for key, val in list(SHORT_MODEL_MAP.items())])
EXCHANGE_SEARCH_MODEL_NAMES_REVERSE = dict([(val, key) for key, val in list(EXCHANGE_SEARCH_MODEL_NAMES.items())])


def itemid_from_searchresult(result):
    """ Returns a unique long id for a haystack result without revealing any DB ids. 
        itemid: <portal_id>.<modeltype>.<slug>
        Example:  `1.people.saschanarr` """
    if result.portal == settings.COSINNUS_EXCHANGE_PORTAL_ID:
        model_name = EXCHANGE_SEARCH_MODEL_NAMES[result.model]
    else:  
        model_name = SEARCH_MODEL_NAMES[result.model]
    slug = result.slug
    if model_name == 'events':
        slug = '%s*%s' % (result.group_slug, slug)
    return '%d.%s.%s' % (result.portal or 0, model_name, slug)


def filter_event_searchqueryset_by_upcoming(sqs):
    # upcoming events
    _now = now()
    event_horizon = datetime.datetime(_now.year, _now.month, _now.day)
    sqs = sqs.exclude(Q(to_date__lt=event_horizon) | (Q(_missing_='to_date') & Q(from_date__lt=event_horizon)))
    # only actual events, no doodles
    sqs = sqs.exclude(Q(event_state__lt=1) | Q(event_state__gt=1))
    return sqs

def build_date_time(date_string, time_string):

    if date_string:
        time_zone = timezone.get_current_timezone_name()
        time_zone = pytz.timezone(time_zone)

        format_string = "%Y-%m-%d"
        if date_string and time_string:
            format_string = "%Y-%m-%d %H:%M"

        date_time_string = date_string
        if time_string:
            date_time_string = '{} {}'.format(date_string, time_string)

        try:
            date_time = datetime.datetime.strptime(date_time_string, format_string)
        except ValueError:
            date_time = datetime.datetime.strptime(date_string, "%Y-%m-%d")

        date_time = time_zone.localize(date_time)
        return date_time

def filter_event_or_conference_happening_during(from_datetime, to_datetime, sqs):
    """ Filters all events or conferences to retain those happening during the provided
        datetime range, either fully or in part. """
    sqs = sqs.exclude(to_date__lt=from_datetime).exclude(from_date__gt=to_datetime)
    return sqs
