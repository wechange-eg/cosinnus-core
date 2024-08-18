import logging

from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model
from django.db.models import Case, Count, When
from django.templatetags.static import static
from django.urls.base import reverse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal, get_cosinnus_group_model, get_domain_for_portal
from cosinnus.models.group_extra import CosinnusConference
from cosinnus.models.user_dashboard import DashboardItem, MenuItem
from cosinnus.trans.group import CosinnusConferenceTrans, CosinnusProjectTrans, CosinnusSocietyTrans
from cosinnus.utils.dates import datetime_from_timestamp, timestamp_from_datetime
from cosinnus.utils.functions import resolve_class
from cosinnus.utils.permissions import (
    check_user_can_create_conferences,
    check_user_can_create_groups,
    check_user_portal_manager,
)
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.user import get_unread_message_count_for_user
from cosinnus.utils.version_history import get_version_history_for_user, mark_version_history_as_read
from cosinnus.views.user_dashboard import MyGroupsClusteredMixin
from cosinnus_notifications.models import NotificationAlert, SerializedNotificationAlert

logger = logging.getLogger('cosinnus')


class SpacesView(MyGroupsClusteredMixin, APIView):
    """
    An endpoint that provides the user spaces for the main navigation.
    Returns items (menu item list) and actions (menu item list) for the different spaces:
    - Personal-Space: users personal dashboard
    - Projects and Groups: users projects and groups
    - Community: Forum and Map
    - Conferences: users conferences
    Each menu item contains: id, label (HTML), url, is_external, icon (Font Awesome class, optional),
    image url (optional), badge (optional), selected.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'personal': {
                                'header': 'My Personal Space',
                                'items': [
                                    {
                                        'id': 'PersonalDashboard',
                                        'label': 'Personal Dashboard',
                                        'url': '/dashboard/',
                                        'is_external': False,
                                        'icon': None,
                                        'image': 'http://localhost:8000/media/image.png',
                                        'badge': None,
                                        'selected': False,
                                    }
                                ],
                                'actions': [],
                            },
                            'groups': {
                                'header': 'My Groups and Projects',
                                'items': [
                                    {
                                        'id': 'CosinnusSociety70',
                                        'label': 'Test Group',
                                        'url': '/group/test-group/',
                                        'is_external': False,
                                        'icon': None,
                                        'image': 'http://localhost:8000/media/image.png',
                                        'badge': None,
                                        'selected': False,
                                    }
                                ],
                                'actions': [
                                    {
                                        'id': 'CreateGroup',
                                        'label': 'Create a Group',
                                        'url': '/groups/add/',
                                        'is_external': False,
                                        'icon': None,
                                        'image': None,
                                        'badge': None,
                                        'selected': False,
                                    },
                                    {
                                        'id': 'CreateProject',
                                        'label': 'Create a Project',
                                        'url': '/projects/add/',
                                        'is_external': False,
                                        'icon': None,
                                        'image': None,
                                        'badge': None,
                                        'selected': False,
                                    },
                                ],
                            },
                            'community': {
                                'header': 'WECHANGE Community',
                                'items': [
                                    {
                                        'id': 'Forum',
                                        'label': 'Forum',
                                        'url': '/group/forum/',
                                        'is_external': False,
                                        'icon': 'fa-sitemap',
                                        'image': None,
                                        'badge': None,
                                        'selected': False,
                                    },
                                    {
                                        'id': 'Map',
                                        'label': 'Map',
                                        'url': '/map/',
                                        'is_external': False,
                                        'icon': 'fa-group',
                                        'image': None,
                                        'badge': None,
                                        'selected': False,
                                    },
                                ],
                                'actions': [],
                            },
                            'conference': {
                                'header': 'My Conferences',
                                'items': [
                                    {
                                        'id': 'CosinnusSociety70',
                                        'label': 'Test Conference',
                                        'url': '/conference/test-conference/',
                                        'is_external': False,
                                        'icon': 'fa-television',
                                        'image': None,
                                        'badge': None,
                                        'selected': False,
                                    }
                                ],
                                'actions': [
                                    {
                                        'id': 'CreateConference',
                                        'label': 'Create a Conference',
                                        'url': '/conferences/add/',
                                        'is_external': False,
                                        'icon': None,
                                        'image': None,
                                        'badge': None,
                                        'selected': False,
                                    }
                                ],
                            },
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        spaces = {}

        # personal space
        personal_space = None
        if request.user.is_authenticated:
            personal_space_items = [
                MenuItem(
                    _('Personal Dashboard'),
                    reverse('cosinnus:user-dashboard'),
                    'fa-user',
                    request.user.cosinnus_profile.avatar_url,
                    id='PersonalDashboard',
                )
            ]
            personal_space = {
                'header': _('My Personal Space'),
                'items': personal_space_items,
                'actions': [],
            }
        spaces['personal'] = personal_space

        # projects and groups
        group_space = None
        group_space_items = []
        group_space_actions = []
        if request.user.is_authenticated:
            group_space_items = [
                dashboard_item.as_menu_item()
                for cluster in self.get_group_clusters(request.user)
                for dashboard_item in cluster
            ]
        if not settings.COSINNUS_SHOW_MAIN_MENU_GROUP_CREATE_BUTTON_ONLY_FOR_PERMITTED or check_user_can_create_groups(
            request.user
        ):
            group_space_actions = [
                MenuItem(CosinnusSocietyTrans.CREATE_NEW, reverse('cosinnus:group__group-add'), id='CreateGroup'),
                MenuItem(CosinnusProjectTrans.CREATE_NEW, reverse('cosinnus:group-add'), id='CreateProject'),
            ]
        if group_space_items or group_space_actions:
            group_space = {
                'header': _('My Groups and Projects'),
                'items': group_space_items,
                'actions': group_space_actions,
            }
        spaces['groups'] = group_space

        # community
        community_space = None
        community_space_items = []
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        events_slug = getattr(settings, 'NEWW_EVENTS_GROUP_SLUG', None)
        if forum_slug:
            forum_group = get_object_or_None(
                get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current()
            )
            if forum_group:
                if (
                    settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_LINKS_FROM_MANAGED_TAG_GROUPS
                    and request.user.is_authenticated
                ):
                    # Add paired_groups of managed tags to community space.
                    managed_tags = self.request.user.cosinnus_profile.get_managed_tags()
                    if managed_tags:
                        for tag in managed_tags:
                            if tag and tag.paired_group and tag.paired_group != forum_group:
                                community_space_items.append(
                                    MenuItem(
                                        tag.paired_group.name,
                                        tag.paired_group.get_absolute_url(),
                                        'fa-group',
                                        id=f'Forum{tag.paired_group.id}',
                                    )
                                )
                # add Forum group to community space
                if settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL:
                    community_space_items.append(
                        MenuItem(
                            settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL,
                            forum_group.get_absolute_url(),
                            'fa-sitemap',
                            id='Forum',
                        )
                    )
                # add Events-Forum group to community space for portals that have a split Events Forum group
                if events_slug != forum_slug:
                    events_group = get_object_or_None(
                        get_cosinnus_group_model(), slug=events_slug, portal=CosinnusPortal.get_current()
                    )
                    if events_group:
                        community_space_items.append(
                            MenuItem(
                                events_group['name'],
                                events_group.get_absolute_url(),
                                'fa-calendar',
                                id='Events',
                            )
                        )
        # "Discover" link in community section of spaces menu
        if settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL:
            community_space_items.append(
                MenuItem(settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL, reverse('cosinnus:map'), 'fa-map', id='Map')
            )
        if settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS:
            community_space_items.extend(
                [
                    MenuItem(label, url, icon, id=id)
                    for id, label, url, icon in settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS
                ]
            )
        if community_space_items:
            community_space_actions = [
                MenuItem(CosinnusSocietyTrans.BROWSE_ALL, reverse('cosinnus:group__group-list'), id='BrowseGroups'),
                MenuItem(CosinnusProjectTrans.BROWSE_ALL, reverse('cosinnus:group-list'), id='BrowseProjects'),
            ]
            community_space = {
                'header': f'{settings.COSINNUS_PORTAL_NAME.upper()} {_("Community")}',
                'items': community_space_items,
                'actions': community_space_actions,
            }
        spaces['community'] = community_space

        # conferences
        if settings.COSINNUS_CONFERENCES_ENABLED:
            conference_space = None
            conference_space_items = []
            conference_space_actions = []
            if request.user.is_authenticated:
                conferences = CosinnusConference.objects.get_for_user(request.user)
                conference_space_items = [DashboardItem(conference).as_menu_item() for conference in conferences]
            if (
                not settings.COSINNUS_SHOW_MAIN_MENU_CONFERENCE_CREATE_BUTTON_ONLY_FOR_PERMITTED
                or check_user_can_create_conferences(request.user)
            ):
                conference_space_actions = [
                    MenuItem(
                        CosinnusConferenceTrans.CREATE_NEW,
                        reverse('cosinnus:conference__group-add'),
                        id='CreateConference',
                    ),
                    MenuItem(
                        CosinnusConferenceTrans.BROWSE_ALL,
                        reverse('cosinnus:conference__group-list'),
                        id='BrowseConferenes',
                    ),
                ]
            if conference_space_items or conference_space_actions:
                conference_space = {
                    'header': _('My Conferences'),
                    'items': conference_space_items,
                    'actions': conference_space_actions,
                }
            spaces['conference'] = conference_space

        return Response(spaces)


class BookmarksView(APIView):
    """
    An endpoint that provides the user bookmarks for the main navigation.
    Returns menu items for liked groups and projects, liked users and liked content (e.g. ideas).
    Each menu item contains: id, label (HTML), url, is_external, icon (Font Awesome class, optional),
    image url (optional), badge (optional), selected.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'groups': {
                                'header': 'Groups and Projects',
                                'items': {
                                    'id': 'CosinnusGroup70',
                                    'label': 'Test Group',
                                    'url': '/group/test-group/',
                                    'is_external': False,
                                    'icon': None,
                                    'image': 'http://localhost:8000/media/image.png',
                                    'badge': None,
                                    'selected': False,
                                },
                            },
                            'users': {
                                'header': 'Users',
                                'items': {
                                    'id': 'UserProfile4',
                                    'label': 'Test User',
                                    'url': '/user/2/',
                                    'is_external': False,
                                    'icon': 'fa-user',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                            },
                            'content': {
                                'header': 'Content',
                                'items': {
                                    'id': 'CosinnusIdea2',
                                    'label': 'Test Idea',
                                    'url': '/map/?item=1.ideas.test-idea',
                                    'is_external': False,
                                    'icon': 'fa-lightbulb-o',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                            },
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        bookmarks = None
        group_items = []
        content_items = []
        if request.user.is_authenticated:
            try:
                liked_users = request.user.cosinnus_profile.get_user_starred_users()
                user_items = [DashboardItem(user).as_menu_item() for user in liked_users]
                liked_objects = request.user.cosinnus_profile.get_user_starred_objects()
                for liked_object in liked_objects:
                    if isinstance(liked_object, get_cosinnus_group_model()):
                        group_items.append(DashboardItem(liked_object).as_menu_item())
                    else:
                        content_items.append(DashboardItem(liked_object).as_menu_item())
                if group_items or user_items or content_items:
                    bookmarks = {
                        'groups': {
                            'header': _('Groups and Projects'),
                            'items': group_items,
                        },
                        'users': {
                            'header': _('Users'),
                            'items': user_items,
                        },
                        'content': {
                            'header': pgettext('navigation bookmarks header', 'Content'),
                            'items': content_items,
                        },
                    }
            except Exception as e:
                logger.error(
                    'An error occurred in the navigation API!',
                    extra={'exception': force_str(e), 'user': request.user},
                )
        return Response(bookmarks)


class UnreadMessagesView(APIView):
    """An endpoint that returns the user unread message count for the main navigation."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {'count': 10},
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        unread_message_count = 0
        if request.user.is_authenticated:
            unread_message_count = get_unread_message_count_for_user(request.user)
        unread_messages = {
            'count': unread_message_count,
        }
        return Response(unread_messages)


class UnreadAlertsView(APIView):
    """An endpoint that returns the user unseen alerts count for the main navigation."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {'count': 10},
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        alerts_count = 0
        if request.user.is_authenticated:
            alerts_qs = NotificationAlert.objects.filter(portal=CosinnusPortal.get_current(), user=self.request.user)
            unseen_aggr = alerts_qs.aggregate(seen_count=Count(Case(When(seen=False, then=1))))
            alerts_count = unseen_aggr.get('seen_count', 0)
        unread_alerts = {'count': alerts_count}
        return Response(unread_alerts)


class AlertsView(APIView):
    """
    An endpoint that provides the user alerts for the main navigation.
    Returns a list of alert items, consisting of a text (label), url, icon, image, action_datetime and additional
    alert details. Unread alerts are marked via "is_emphasized".

    Multiple related alerts are bundled in a single alert item as sub_items:
    - is_multi_user_alert: is for events happening on a single content object, but with multiple users acting on it.
    - is_bundle_alert: is a single alert object bundled for multiple content objects causing events in a short
      time frame, all by the same user in the same group.

    Each sub alert contains text (label), url, icon and image elements.
    The response list is paginated by 10 items. For pagination the "offset_timestamp" parameter should be used.
    To receive new alerts the "newer_than_timestamp" should be used.

    Additionally, the retrieved alerts can be marked as read/seen using the "mark_as_read=true" query parameter.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema

    page_size = 10
    newer_than_timestamp = None
    offset_timestamp = None
    mark_as_read = False

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'newer_than_timestamp',
                openapi.IN_QUERY,
                required=False,
                description='Return alerts newer then this timestamp. Used to receive new alerts since the last poll',
                type=openapi.FORMAT_FLOAT,
            ),
            openapi.Parameter(
                'offset_timestamp',
                openapi.IN_QUERY,
                required=False,
                description='Return alerts older then this timestamp. Used for pagination.',
                type=openapi.FORMAT_FLOAT,
            ),
            openapi.Parameter(
                'mark_as_read',
                openapi.IN_QUERY,
                required=False,
                description='Mark unread alerts as read.',
                type=openapi.TYPE_BOOLEAN,
            ),
        ],
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'items': [
                                {
                                    'text': '<b>User 2</b> requested to become a member.',
                                    'id': 'Alert3',
                                    'url': '/group/test-group/members/',
                                    'item_icon': 'fa-sitemap',
                                    'item_image': None,
                                    'user_icon': None,
                                    'user_image': '/static/images/jane-doe-small.png',
                                    'group': 'Test Group',
                                    'group_icon': 'fa-sitemap',
                                    'action_datetime': '2023-06-08T08:49:49.965634+00:00',
                                    'is_emphasized': True,
                                    'alert_reason': 'You are an admin of this team',
                                    'sub_items': [],
                                    'is_multi_user_alert': False,
                                    'is_bundle_alert': False,
                                },
                                {
                                    'text': '<b>User 3</b> und 1 other requested to become a member.',
                                    'id': 'Alert2',
                                    'url': '/group/test-project/members/',
                                    'item_icon': 'fa-group',
                                    'item_image': None,
                                    'user_icon': None,
                                    'user_image': '/static/images/jane-doe-small.png',
                                    'group': 'Test Project',
                                    'group_icon': 'fa-group',
                                    'action_datetime': '2023-05-20T16:04:36.501003+00:00',
                                    'is_emphasized': False,
                                    'alert_reason': 'You are an admin of this team',
                                    'sub_items': [
                                        {
                                            'title': 'User 3',
                                            'url': '/user/4/',
                                            'icon': None,
                                            'image': '/static/images/jane-doe-small.png',
                                        },
                                        {
                                            'title': 'User 4',
                                            'url': '/user/5/',
                                            'icon': None,
                                            'image': '/static/images/jane-doe-small.png',
                                        },
                                    ],
                                    'is_multi_user_alert': True,
                                    'is_bundle_alert': False,
                                },
                                {
                                    'text': '<b>User 2</b> created 2 news posts.',
                                    'id': 'Alert1',
                                    'url': '/group/test-group/note/1401481714/',
                                    'item_icon': 'fa-quote-right',
                                    'item_image': None,
                                    'user_icon': None,
                                    'user_image': '/static/images/jane-doe-small.png',
                                    'group': 'Test Group',
                                    'group_icon': 'fa-sitemap',
                                    'action_datetime': '2023-05-24T08:44:50.570918+00:00',
                                    'is_emphasized': True,
                                    'alert_reason': 'You are following this content or its Project or Group',
                                    'sub_items': [
                                        {
                                            'title': 'test2',
                                            'url': '/group/test-group/note/1455745550/',
                                            'icon': 'fa-quote-right',
                                            'image': None,
                                        },
                                        {
                                            'title': 'test',
                                            'url': '/group/test-group/note/1401481714/',
                                            'icon': 'fa-quote-right',
                                            'image': None,
                                        },
                                    ],
                                    'is_multi_user_alert': False,
                                    'is_bundle_alert': True,
                                },
                            ],
                            'has_more': False,
                            'offset_timestamp': 1684917890.570918,
                            'newest_timestamp': 1686664282.772708,
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def get(self, request):
        response = {
            'items': [],
            'has_more': False,
            'offset_timestamp': None,
            'newest_timestamp': None,
        }
        if request.user.is_authenticated:
            self.read_query_params(request)
            queryset = self.get_queryset()

            # has_more
            response['has_more'] = queryset.count() > self.page_size

            # paginate
            queryset = queryset[: self.page_size]
            alerts = list(queryset)

            # mark as read
            if self.mark_as_read:
                for alert in alerts:
                    alert.seen = True
                NotificationAlert.objects.bulk_update(alerts, ['seen'])

            # alert items
            user_cache = self.get_user_cache(alerts)
            items = []
            for alert in alerts:
                serialized_alert = SerializedNotificationAlert(
                    alert,
                    action_user=user_cache[alert.action_user_id][0],
                    action_user_profile=user_cache[alert.action_user_id][1],
                )
                # split "icon_or_image_url"
                self._split_icon_or_image_url(serialized_alert, 'item_')
                self._split_icon_or_image_url(serialized_alert, 'user_')
                for sub_item in serialized_alert.get('sub_items', []):
                    self._split_icon_or_image_url(sub_item)
                # use relative urls
                self._use_relative_url(serialized_alert)
                for sub_item in serialized_alert.get('sub_items', []):
                    self._use_relative_url(sub_item)
                # Use string identifier
                serialized_alert['id'] = f'Alert{serialized_alert["id"]}'
                items.append(serialized_alert)
            response['items'] = items

            # newest timestamp
            if not self.offset_timestamp and len(alerts) > 0:
                newest_timestamp = timestamp_from_datetime(alerts[0].last_event_at)
                response['newest_timestamp'] = newest_timestamp

            # offset timestamp
            if len(alerts) > 0:
                offset_timestamp = timestamp_from_datetime(alerts[-1].last_event_at)
                response['offset_timestamp'] = offset_timestamp

        return Response(response)

    def read_query_params(self, request):
        self.newer_than_timestamp = request.query_params.get('newer_than_timestamp')
        if self.newer_than_timestamp:
            try:
                self.newer_than_timestamp = float(self.newer_than_timestamp)
            except Exception:
                raise ValidationError({'newer_than_timestamp': 'Float timestamp expected'})
        self.offset_timestamp = request.query_params.get('offset_timestamp')
        if self.offset_timestamp:
            try:
                self.offset_timestamp = float(self.offset_timestamp)
            except Exception:
                raise ValidationError({'offset_timestamp': 'Float timestamp expected'})
        self.mark_as_read = request.query_params.get('mark_as_read') == 'true'

    def get_queryset(self):
        alerts_qs = NotificationAlert.objects.filter(portal=CosinnusPortal.get_current(), user=self.request.user)
        if self.newer_than_timestamp:
            after_dt = datetime_from_timestamp(self.newer_than_timestamp)
            alerts_qs = alerts_qs.filter(last_event_at__gt=after_dt)
        elif self.offset_timestamp:
            before_datetime = datetime_from_timestamp(self.offset_timestamp)
            alerts_qs = alerts_qs.filter(last_event_at__lt=before_datetime)
        return alerts_qs

    def get_user_cache(self, alerts):
        user_ids = list(set([alert.action_user_id for alert in alerts]))
        users = get_user_model().objects.filter(id__in=user_ids).prefetch_related('cosinnus_profile')
        user_cache = dict(((user.id, (user, user.cosinnus_profile)) for user in users))
        return user_cache

    def _use_relative_url(self, serialized_alert):
        """Replace url with relative url."""
        url = serialized_alert.get('url')
        if url:
            domain = get_domain_for_portal(CosinnusPortal.get_current())
            if url.startswith(domain):
                serialized_alert['url'] = url.replace(domain, '')

    def _split_icon_or_image_url(self, serialized_alert, key_prefix=''):
        """Replace icon_or_image_url items with separate icon and image items. Use absolute url for images."""
        icon_or_image_url = serialized_alert.pop(key_prefix + 'icon_or_image_url')
        if not icon_or_image_url:
            serialized_alert[key_prefix + 'icon'] = None
            serialized_alert[key_prefix + 'image'] = None
        elif icon_or_image_url.startswith('fa-'):
            serialized_alert[key_prefix + 'icon'] = icon_or_image_url
            serialized_alert[key_prefix + 'image'] = None
        else:
            domain = get_domain_for_portal(CosinnusPortal.get_current())
            if icon_or_image_url.startswith('/'):
                icon_or_image_url = domain + icon_or_image_url
            serialized_alert[key_prefix + 'image'] = icon_or_image_url
            serialized_alert[key_prefix + 'icon'] = None


class HelpView(APIView):
    """
    An endpoint that returns a list of help menu items for the main navigation.
    Each menu item contains: id, label (HTML), url, is_external, icon (Font Awesome class, optional),
    image url (optional), badge (optional), selected.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': [
                            {
                                'id': 'FAQ',
                                'label': '<b>FAQ</b>',
                                'url': 'https://localhost/cms/faq/',
                                'is_external': True,
                                'icon': 'fa-question-circle',
                                'image': None,
                                'badge': None,
                                'selected': False,
                            },
                            {
                                'id': 'Support',
                                'label': '<b>Support-Channel</b> (Chat)',
                                'url': 'https://localhost/cms/support/',
                                'is_external': True,
                                'icon': 'fa-life-ring',
                                'image': None,
                                'badge': None,
                                'selected': False,
                            },
                        ],
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        help_items = [
            MenuItem(label, url, icon, is_external=True, id=id)
            for id, label, url, icon in settings.COSINNUS_V3_MENU_HELP_LINKS
        ]
        return Response(help_items)


class LanguageMenuItemMixin:
    def get_language_menu_item(self, request, current_language_as_label=False):
        language_item_label = request.LANGUAGE_CODE.upper() if current_language_as_label else _('Change Language')
        language_item_icon = None if current_language_as_label else 'fa-language'
        language_item = MenuItem(language_item_label, icon=language_item_icon, id='ChangeLanguage')
        if settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES:
            language_selection = filter(
                lambda lang: lang[0] in settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES, settings.LANGUAGES
            )
        else:
            language_selection = settings.LANGUAGES
        language_subitems = []
        for code, language in language_selection:
            selected = code == request.LANGUAGE_CODE
            language_subitem = MenuItem(
                language,
                reverse('cosinnus:switch-language', kwargs={'language': code}),
                icon=None if current_language_as_label else 'fa-language',
                id=f'ChangeLanguageItem{code.upper()}',
                selected=selected,
            )
            language_subitems.append(language_subitem)
        language_item['sub_items'] = language_subitems
        return language_item


class ProfileView(LanguageMenuItemMixin, APIView):
    """
    An endpoint that provides user profile menu items for the main navigation.
    Returns a list of menu items for user profile and notification settings, contribution, administration, logout and a
    language switcher item. The language switcher item contains a list of menu items for the available languages.
    Each menu item contains: id, label (HTML), url, is_external, icon (Font Awesome class, optional),
    image url (optional), badge (optional), selected.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': [
                            {
                                'id': 'Profile',
                                'label': 'My Profile',
                                'url': '/profile/',
                                'is_external': False,
                                'icon': 'fa-circle-user',
                                'image': None,
                                'badge': None,
                                'selected': False,
                            },
                            {
                                'id': 'NotificationPreferences',
                                'label': 'Notification Preferences',
                                'url': '/profile/notifications/',
                                'is_external': False,
                                'icon': 'fa-envelope',
                                'image': None,
                                'badge': None,
                                'selected': False,
                            },
                            {
                                'id': 'Contribution',
                                'label': 'Your Contribution',
                                'url': '/account/contribution/',
                                'is_external': False,
                                'icon': 'fa-hand-holding-hart',
                                'image': None,
                                'badge': None,
                                'selected': False,
                            },
                            {
                                'id': 'Logout',
                                'label': 'Logout',
                                'url': '/logout/',
                                'is_external': False,
                                'icon': 'fa-right-from-bracket',
                                'image': None,
                                'badge': None,
                                'selected': False,
                            },
                        ],
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        profile_menu = None

        if request.user.is_authenticated:
            profile_menu = []

            profile_label = _('My Profile')
            if request.user.is_guest:
                profile_label = _('My Guest Account')
            # profile pages
            profile_menu_items = [
                MenuItem(profile_label, reverse('cosinnus:profile-detail'), 'fa-circle-user', id='Profile'),
            ]
            if not request.user.is_guest:
                profile_menu_items.extend(
                    [
                        MenuItem(
                            _('Notification Preferences'),
                            reverse('cosinnus:notifications'),
                            'fa-envelope',
                            id='NotificationPreferences',
                        ),
                    ]
                )
            profile_menu.extend(profile_menu_items)

            # payments
            if (
                not request.user.is_guest
                and settings.COSINNUS_PAYMENTS_ENABLED
                or settings.COSINNUS_PAYMENTS_ENABLED_ADMIN_ONLY
                and request.user.is_superuser
            ):
                from wechange_payments.models import Subscription

                current_subscription = Subscription.get_current_for_user(request.user)
                contribution = int(current_subscription.amount) if current_subscription else 0
                contribution_badge = f'{contribution} €'
                payments_item = MenuItem(
                    _('Your Contribution'),
                    reverse('wechange-payments:overview'),
                    'fa-hand-holding-hart',
                    badge=contribution_badge,
                    id='Contribution',
                )
                profile_menu.append(payments_item)

            # administration
            if request.user.is_superuser or check_user_portal_manager(request.user):
                administration_item = MenuItem(
                    _('Administration'),
                    reverse('cosinnus:administration'),
                    'fa-screwdriver-wrench',
                    id='Administration',
                )
                profile_menu.append(administration_item)

            # logout
            logout_label = _('Logout')
            if request.user.is_guest:
                logout_label = _('Leave guest access')
            logout_item = MenuItem(logout_label, reverse('logout'), 'fa-right-from-bracket', id='Logout')
            profile_menu.append(logout_item)

        return Response(profile_menu)


class MainNavigationView(LanguageMenuItemMixin, APIView):
    """
    An endpoint that provides menu items for main navigation.
    It contains pseudo menu items just to indicate the availability of a menu-item (e.g. for spaces and search) or
    actual menu items (e.g. cloud, login). The content of the main navigation differs for authenticated and
    non-authenticated users.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'left': [
                                {
                                    'id': 'Home',
                                    'label': 'Home',
                                    'url': '/cms/?noredir=1',
                                    'is_external': False,
                                    'icon': None,
                                    'image': 'http://localhost:8000/static/img/logo-icon.png',
                                    'badge': None,
                                    'selected': False,
                                },
                                {
                                    'id': 'Spaces',
                                    'label': 'Spaces',
                                    'url': None,
                                    'is_external': False,
                                    'icon': None,
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                            ],
                            'middle': [
                                {
                                    'id': 'Search',
                                    'label': 'Search',
                                    'url': '/search/',
                                    'is_external': False,
                                    'icon': 'fa-magnifying-glass',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                                {
                                    'id': 'Bookmarks',
                                    'label': 'Bookmarks',
                                    'url': None,
                                    'is_external': False,
                                    'icon': 'fa-bookmark',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                            ],
                            'services': [
                                {
                                    'id': 'Cloud',
                                    'label': 'Cloud',
                                    'url': 'https://cloud.localhost/',
                                    'is_external': True,
                                    'icon': 'fa-cloud',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                                {
                                    'id': 'Chat',
                                    'label': 'Rocket.Chat',
                                    'url': '/messages/',
                                    'is_external': False,
                                    'icon': 'messages',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                            ],
                            'right': [
                                {
                                    'id': 'Help',
                                    'label': 'Help',
                                    'url': None,
                                    'is_external': False,
                                    'icon': 'fa-question',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                                {
                                    'id': 'Alerts',
                                    'label': 'Alerts',
                                    'url': None,
                                    'is_external': False,
                                    'icon': 'fa-bell',
                                    'image': None,
                                    'badge': None,
                                    'selected': False,
                                },
                                {
                                    'id': 'Profile',
                                    'label': 'Profile',
                                    'url': None,
                                    'is_external': False,
                                    'icon': None,
                                    'image': 'http://localhost:8000/media/image.png',
                                    'badge': None,
                                    'selected': False,
                                },
                            ],
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        main_navigation_items = {
            'left': None,
            'middle': None,
            'services': None,
            'right': None,
        }

        # left part
        left_navigation_items = []

        # home
        current_portal = CosinnusPortal.get_current()
        home_image = '%s%s' % (current_portal.get_domain(), static(settings.COSINNUS_PORTAL_LOGO_NAVBAR_IMAGE_URL))
        if settings.COSINNUS_V3_MENU_HOME_LINK:
            home_item = MenuItem(
                _('Home'), settings.COSINNUS_V3_MENU_HOME_LINK, icon='fa-home', image=home_image, id='Home'
            )
        else:
            home_item = MenuItem(
                _('Dashboard'), reverse('cosinnus:user-dashboard'), icon='fa-home', image=home_image, id='HomeDashboard'
            )
        left_navigation_items.append(home_item)

        # spaces
        left_navigation_items.append(MenuItem('Spaces', id='Spaces'))

        # middle part
        middle_navigation_items = []

        # search
        if request.user.is_authenticated:
            middle_navigation_items.append(
                MenuItem(_('Search'), reverse('cosinnus:search'), 'fa-magnifying-glass', id='Search')
            )

        if request.user.is_authenticated:
            # bookmarks
            middle_navigation_items.append(MenuItem(_('Bookmarks'), icon='fa-bookmark', id='Bookmarks'))

        # services part
        services_navigation_items = []

        if request.user.is_authenticated and not request.user.is_guest:
            # cloud
            if settings.COSINNUS_CLOUD_ENABLED:
                services_navigation_items.append(
                    MenuItem(
                        _('Cloud'),
                        settings.COSINNUS_CLOUD_NEXTCLOUD_URL,
                        icon='fa-cloud',
                        is_external=settings.COSINNUS_CLOUD_OPEN_IN_NEW_TAB,
                        id='Cloud',
                    )
                )

            # messages
            if 'cosinnus_message' not in settings.COSINNUS_DISABLED_COSINNUS_APPS:
                if settings.COSINNUS_ROCKET_ENABLED:
                    services_navigation_items.append(
                        MenuItem(
                            'Rocket.Chat',
                            reverse('cosinnus:message-global'),
                            icon='messages',
                            is_external=settings.COSINNUS_ROCKET_OPEN_IN_NEW_TAB,
                            id='Chat',
                        )
                    )
                else:
                    services_navigation_items.append(
                        MenuItem(_('Messages'), reverse('postman:inbox'), icon='messages', id='Messages')
                    )
        # add "Calendar" link to services for all logged in users if the portal has a seperate Events forum group
        if request.user.is_authenticated:
            if settings.NEWW_EVENTS_GROUP_SLUG and settings.NEWW_EVENTS_GROUP_SLUG != settings.NEWW_FORUM_GROUP_SLUG:
                events_url = group_aware_reverse(
                    'cosinnus:event:list', kwargs={'group': settings.NEWW_EVENTS_GROUP_SLUG}
                )
                services_navigation_items.insert(
                    0, MenuItem(_('Events'), events_url, icon='fa-calendar', is_external=False, id='Events')
                )
        # add "Discover" link to services for non-logged-in users on open portals
        if not settings.COSINNUS_USER_EXTERNAL_USERS_FORBIDDEN and not request.user.is_authenticated:
            services_navigation_items.insert(
                0,
                MenuItem(
                    settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL,
                    reverse('cosinnus:map'),
                    icon='fa-map',
                    is_external=False,
                    id='Map',
                ),
            )

        # right part
        right_navigation_items = []

        # help
        right_navigation_items.append(MenuItem(_('Help'), icon='fa-question', id='Help'))

        if request.user.is_authenticated:
            # alerts
            if not request.user.is_guest:
                right_navigation_items.append(MenuItem(_('Alerts'), icon='fa-bell', id='Alerts'))

            # profile
            right_navigation_items.append(
                MenuItem(_('Profile'), icon='fa-user', image=request.user.cosinnus_profile.avatar_url, id='Profile')
            )
        else:
            # language
            if not settings.COSINNUS_LANGUAGE_SELECT_DISABLED:
                language_item = self.get_language_menu_item(request, current_language_as_label=True)
                right_navigation_items.append(language_item)

            # login
            right_navigation_items.append(MenuItem(_('Login'), reverse('login'), id='Login'))

            # register
            if settings.COSINNUS_USER_SIGNUP_ENABLED:
                right_navigation_items.append(MenuItem(_('Register'), reverse('cosinnus:user-add'), id='Register'))

        main_navigation_items['left'] = left_navigation_items
        main_navigation_items['middle'] = middle_navigation_items
        main_navigation_items['services'] = services_navigation_items
        main_navigation_items['right'] = right_navigation_items

        # allow portals to add links via a dropin defined in `COSINNUS_V3_MENU_PORTAL_LINKS_DROPIN`
        main_navigation_items = CosinnusNavigationPortalLinks().modifiy_main_navigation(
            main_navigation_items, request.user
        )

        return Response(main_navigation_items)


class VersionHistoryView(APIView):
    """
    An endpoint that provides version history for the user.
    It returns a list of information for the latest version, each containing the following fields: id, version title,
    text, url and read. It also returns a menu item for the "show all" link.
    The parameter "mark_as_read=true" can be passed to mark the unread version notes as read.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'mark_as_read',
                openapi.IN_QUERY,
                required=False,
                description='Mark unread versions as read.',
                type=openapi.TYPE_BOOLEAN,
            ),
        ],
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'versions': [
                                {
                                    'id': 'Version123',
                                    'version': '1.2.3',
                                    'title': 'Version 1.2.3 released',
                                    'text': 'Adds some nice features.',
                                    'url': '/whats_new/#123',
                                    'read': False,
                                }
                            ],
                            'show_all': {
                                'id': 'ShowAll',
                                'label': 'Show all',
                                'url': '/whats_new/',
                                'is_external': False,
                                'icon': None,
                                'image': None,
                                'badge': None,
                                'selected': False,
                            },
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def get(self, request):
        version_history = None
        if request.user.is_authenticated:
            version_history = {}

            # get versions
            versions = []
            user_versions, unread_count = get_version_history_for_user(request.user)
            for version in user_versions:
                # serialize version data for the navigation dropdown.
                version_for_api = {
                    'id': 'Version' + version['anchor'].replace('-', ''),
                    'version': version['version'],
                    'title': version['title'],
                    'text': version['short_text'],
                    'url': version['url'],
                    'read': version['read'],
                }
                versions.append(version_for_api)
            version_history['versions'] = versions

            # mark as read
            mark_as_read = request.query_params.get('mark_as_read') == 'true'
            if mark_as_read:
                mark_version_history_as_read(request.user)

            # add show all link
            version_history['show_all'] = MenuItem(_('Show all'), reverse('cosinnus:version-history'), id='ShowAll')

        return Response(version_history)


class VersionHistoryUnreadCountView(APIView):
    """An endpoint that returns the user unseen version history elements count for the main navigation."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {'count': 2},
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        unread_versions_count = 0
        if request.user.is_authenticated:
            versions, unread_versions_count = get_version_history_for_user(request.user)
        unread_versions = {
            'count': unread_versions_count,
        }
        return Response(unread_versions)


class CosinnusNavigationPortalLinksBase(object):
    """A class that modifies or provides additional navbar links returned in
    various navigation API endpoints.
    Used by defining an extending class in a portal and specifying that class for
    `COSINNUS_V3_MENU_PORTAL_LINKS_DROPIN`. The class can then modify the
    links returned by the API endpoints."""

    def modifiy_main_navigation(self, main_navigation_items, user=None):
        # noop, override this function in your portal's dropin
        return main_navigation_items


# allow dropin of extending class
CosinnusNavigationPortalLinks = CosinnusNavigationPortalLinksBase
if getattr(settings, 'COSINNUS_V3_MENU_PORTAL_LINKS_DROPIN', None):
    CosinnusNavigationPortalLinks = resolve_class(settings.COSINNUS_V3_MENU_PORTAL_LINKS_DROPIN)
