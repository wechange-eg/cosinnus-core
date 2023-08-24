from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model
from django.db.models import Case, Count, When
from django.urls.base import reverse
from django.utils.translation import ugettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.conf import settings
from cosinnus.models.group import get_cosinnus_group_model, CosinnusPortal, get_domain_for_portal
from cosinnus.models.group_extra import CosinnusConference
from cosinnus.models.user_dashboard import DashboardItem, MenuItem
from cosinnus.trans.group import CosinnusConferenceTrans, CosinnusProjectTrans, CosinnusSocietyTrans
from cosinnus.utils.dates import datetime_from_timestamp, timestamp_from_datetime
from cosinnus.utils.permissions import check_user_can_create_conferences, check_user_can_create_groups, \
    check_user_portal_manager
from cosinnus.utils.user import get_unread_message_count_for_user
from cosinnus.views.user_dashboard import MyGroupsClusteredMixin
from cosinnus_notifications.models import NotificationAlert, SerializedNotificationAlert


class SpacesView(MyGroupsClusteredMixin, APIView):
    """
    An endpoint that provides the user spaces for the main navigation.
    Returns items (menu item list) and actions (menu item list) for the different spaces:
    - Personal-Space: users personal dashboard
    - Projects and Groups: users projects and groups
    - Community: Forum and Map
    - Conferences: users conferences
    Each menu item consists of a label (Markdown), url, icon (Font Awesome class, optional), image url (optional) and
    badge (optional).
    """

    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "personal": {
                            "items": [
                                {
                                    "icon": "fa-user",
                                    "label": "Personal Dashboard",
                                    "url": "/dashboard/",
                                    "image": "/media/cosinnus_portals/portal_default/avatars/user/0e9e945efe3d60bf807d56e336b677f193675fd8.png",
                                }
                            ],
                            "actions": []
                        },
                        "groups": {
                            "items": [
                                {
                                    "icon": "fa-sitemap",
                                    "label": "Test Group",
                                    "url": "/group/test-group/",
                                    "image": "/media/cosinnus_portals/portal_default/avatars/group/be5636c7955c1fd370514c26ffd4b0902dd5232a.png",
                                }
                            ],
                            "actions": [
                                {
                                    "icon": None,
                                    "label": "Create a Group",
                                    "url": "/groups/add/",
                                    "image": None,
                                },
                                {
                                    "icon": None,
                                    "label": "Create a Project",
                                    "url": "/projects/add/",
                                    "image": None,
                                }
                            ]
                        },
                        "community": {
                            "items": [
                                {
                                    "icon": "fa-sitemap",
                                    "label": "Forum",
                                    "url": "/group/forum/",
                                    "image": None,
                                },
                                {
                                    "icon": "fa-group",
                                    "label": "Map",
                                    "url": "/map/",
                                    "image": None,
                                }
                            ],
                            "actions": []
                        },
                        "conference": {
                            "items": [
                                {
                                    "icon": "fa-television",
                                    "label": "Test Conference",
                                    "url": "/conference/test-conference/",
                                    "image": None,
                                }
                            ],
                            "actions": [
                                {
                                    "icon": None,
                                    "label": "Create a Conference",
                                    "url": "/conferences/add/",
                                    "image": None,
                                }
                            ]
                        }
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        spaces = {}

        # personal space
        dashboard_item = MenuItem(
            _('Personal Dashboard'), reverse('cosinnus:user-dashboard'), 'fa-user',
            request.user.cosinnus_profile.avatar_url
        )
        personal_space = {
            'items': [dashboard_item],
            'actions': [],
        }
        spaces['personal'] = personal_space

        # projects and groups
        group_space_items = [
            dashboard_item.as_menu_item()
            for cluster in self.get_group_clusters(request.user) for dashboard_item in cluster
        ]
        group_space_actions = []
        if not settings.COSINNUS_SHOW_MAIN_MENU_GROUP_CREATE_BUTTON_ONLY_FOR_PERMITTED \
                or check_user_can_create_groups(request.user):
            group_space_actions = [
                MenuItem(CosinnusSocietyTrans.CREATE_NEW, reverse('cosinnus:group__group-add')),
                MenuItem(CosinnusProjectTrans.CREATE_NEW, reverse('cosinnus:group-add')),
            ]
        groups_space = {
            'items': group_space_items,
            'actions': group_space_actions,
        }
        spaces['groups'] = groups_space

        # community
        community_space_items = []
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        if forum_slug:
            forum_group = get_object_or_None(get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current())
            if forum_group:
                if settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_LINKS_FROM_MANAGED_TAG_GROUPS:
                    # Add paired_groups of managed tags to community space.
                    managed_tags = self.request.user.cosinnus_profile.get_managed_tags()
                    if managed_tags:
                        for tag in managed_tags:
                            if tag.paired_group and tag.paired_group != forum_group:
                                community_space_items.append(
                                    MenuItem(tag.paired_group.name, tag.paired_group.get_absolute_url(), 'fa-group')
                                )
                if settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL:
                    community_space_items.append(
                        MenuItem(settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL, forum_group.get_absolute_url(), 'fa-sitemap')
                    )
        if settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL:
            community_space_items.append(
                MenuItem(settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL, reverse('cosinnus:map'), 'fa-group')
            )
        if settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS:
            community_space_items.extend([
                MenuItem(label, url, icon)
                for label, url, icon in settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS
            ])
        community_space = {
            'items': community_space_items,
            'actions': [],
        }
        spaces['community'] = community_space

        # conferences
        if settings.COSINNUS_CONFERENCES_ENABLED:
            conferences = CosinnusConference.objects.get_for_user(request.user)
            conference_space_actions = []
            if not settings.COSINNUS_SHOW_MAIN_MENU_CONFERENCE_CREATE_BUTTON_ONLY_FOR_PERMITTED \
                    or check_user_can_create_conferences(request.user):
                conference_space_actions = [
                    MenuItem(CosinnusConferenceTrans.CREATE_NEW, reverse('cosinnus:conference__group-add')),
                ]
            conference_space = {
                'items': [DashboardItem(conference).as_menu_item() for conference in conferences],
                'actions': conference_space_actions,
            }
            spaces['conference'] = conference_space

        return Response(spaces)


class BookmarksView(APIView):
    """
    An endpoint that provides the user bookmarks for the main navigation.
    Returns menu items for liked groups and projects, liked users and liked content (e.g. ideas).
    Each menu item consists of a label (Markdown), url, icon (Font Awesome class, optional), image url (optional) and
    badge (optional).
    """

    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "groups": [
                            {
                                "icon": "fa-sitemap",
                                "label": "Test Group",
                                "url": "/group/test-group/",
                                "image": "/media/cosinnus_portals/portal_default/avatars/group/be5636c7955c1fd370514c26ffd4b0902dd5232a.png",
                            }
                        ],
                        "users": [
                            {
                                "icon": "fa-user",
                                "label": "Test User",
                                "url": "/user/2/",
                                "image": None,
                            }
                        ],
                        "content": [
                            {
                                "icon": "fa-lightbulb-o",
                                "label": "Test Idea",
                                "url": "/map/?item=1.ideas.test-idea",
                                "image": None,
                            }
                        ]
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        liked_users = self.request.user.cosinnus_profile.get_user_starred_users()
        user_items = [DashboardItem(user).as_menu_item() for user in liked_users]
        liked_objects = self.request.user.cosinnus_profile.get_user_starred_objects()
        group_items = []
        content_items = []
        for liked_object in liked_objects:
            if isinstance(liked_object, get_cosinnus_group_model()):
                group_items.append(DashboardItem(liked_object).as_menu_item())
            else:
                content_items.append(DashboardItem(liked_object).as_menu_item())
        bookmarks = {
            'groups': group_items,
            'users': user_items,
            'content': content_items,
        }
        return Response(bookmarks)


class UnreadMessagesView(APIView):
    """ An endpoint that returns the user unread message count for the main navigation. """

    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "count": 10
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        unread_message_count = get_unread_message_count_for_user(request.user)
        unread_messages = {
            'count': unread_message_count,
        }
        return Response(unread_messages)


class UnreadAlertsView(APIView):
    """ An endpoint that returns the user unseen alerts count for the main navigation. """

    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "count": 10
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        alerts_qs = NotificationAlert.objects.filter(portal=CosinnusPortal.get_current(), user=self.request.user)
        unseen_aggr = alerts_qs.aggregate(seen_count=Count(Case(When(seen=False, then=1))))
        unread_alerts = {
            'count': unseen_aggr.get('seen_count', 0)
        }
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

    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
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
                'newer_than_timestamp', openapi.IN_QUERY, required=False,
                description='Return alerts newer then this timestamp. Used to receive new alerts since the last poll',
                type=openapi.FORMAT_FLOAT
            ),
            openapi.Parameter(
                'offset_timestamp', openapi.IN_QUERY, required=False,
                description='Return alerts older then this timestamp. Used for pagination.', type=openapi.FORMAT_FLOAT
            ),
            openapi.Parameter(
                'mark_as_read', openapi.IN_QUERY, required=False,
                description='Mark unread alerts as read.', type=openapi.TYPE_BOOLEAN
            ),
        ],
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "items": [
                            {
                                "text": "<b>User 2</b> requested to become a member.",
                                "id": 3,
                                "url": "/group/test-group/members/",
                                "item_icon": "fa-sitemap",
                                "item_image": None,
                                "user_icon": None,
                                "user_image": "/static/images/jane-doe-small.png",
                                "group": "Test Group",
                                "group_icon": "fa-sitemap",
                                "action_datetime": "2023-06-08T08:49:49.965634+00:00",
                                "is_emphasized": True,
                                "alert_reason": "You are an admin of this team",
                                "sub_items": [],
                                "is_multi_user_alert": False,
                                "is_bundle_alert": False
                            },
                            {
                                "text": "<b>User 3</b> und 1 other requested to become a member.",
                                "id": 2,
                                "url": "/group/test-project/members/",
                                "item_icon": "fa-group",
                                "item_image": None,
                                "user_icon": None,
                                "user_image": "/static/images/jane-doe-small.png",
                                "group": "Test Project",
                                "group_icon": "fa-group",
                                "action_datetime": "2023-05-20T16:04:36.501003+00:00",
                                "is_emphasized": False,
                                "alert_reason": "You are an admin of this team",
                                "sub_items": [
                                    {
                                        "title": "User 3",
                                        "url": "/user/4/",
                                        "icon": None,
                                        "image": "/static/images/jane-doe-small.png",
                                    },
                                    {
                                        "title": "User 4",
                                        "url": "/user/5/",
                                        "icon": None,
                                        "image": "/static/images/jane-doe-small.png",
                                    }
                                ],
                                "is_multi_user_alert": True,
                                "is_bundle_alert": False
                            },
                            {
                                "text": "<b>User 2</b> created 2 news posts.",
                                "id": 1,
                                "url": "/group/test-group/note/1401481714/",
                                "item_icon": "fa-quote-right",
                                "item_image": None,
                                "user_icon": None,
                                "user_image": "/static/images/jane-doe-small.png",
                                "group": "Test Group",
                                "group_icon": "fa-sitemap",
                                "action_datetime": "2023-05-24T08:44:50.570918+00:00",
                                "is_emphasized": True,
                                "alert_reason": "You are following this content or its Project or Group",
                                "sub_items": [
                                    {
                                        "title": "test2",
                                        "url": "/group/test-group/note/1455745550/",
                                        "icon": "fa-quote-right",
                                        "image": None,
                                    },
                                    {
                                        "title": "test",
                                        "url": "/group/test-group/note/1401481714/",
                                        "icon": "fa-quote-right",
                                        "image": None,
                                    }
                                ],
                                "is_multi_user_alert": False,
                                "is_bundle_alert": True
                            }
                        ],
                        "has_more": False,
                        "offset_timestamp": 1684917890.570918,
                        "newest_timestamp": 1686664282.772708
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )},
    )
    def get(self, request):
        self.read_query_params(request)
        response = {
            'items': None,
            'has_more': False,
            'offset_timestamp': None,
            'newest_timestamp': None,
        }
        queryset = self.get_queryset()

        # has_more
        response['has_more'] = queryset.count() > self.page_size

        # paginate
        queryset = queryset[:self.page_size]
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
                self.offset_timestamp= float(self.offset_timestamp)
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
        """ Replace url with relative url. """
        url = serialized_alert.get('url')
        if url:
            domain = get_domain_for_portal(CosinnusPortal.get_current())
            if url.startswith(domain):
                serialized_alert['url'] = url.replace(domain, '')

    def _split_icon_or_image_url(self, serialized_alert, key_prefix=''):
        """ Replace icon_or_image_url items with separate icon and image items. """
        icon_or_image_url = serialized_alert.pop(key_prefix + 'icon_or_image_url')
        if not icon_or_image_url:
            serialized_alert[key_prefix + 'icon'] = None
            serialized_alert[key_prefix + 'image'] = None
        elif icon_or_image_url.startswith('fa-'):
            serialized_alert[key_prefix + 'icon'] = icon_or_image_url
            serialized_alert[key_prefix + 'image'] = None
        else:
            serialized_alert[key_prefix + 'image'] = icon_or_image_url
            serialized_alert[key_prefix + 'icon'] = None


class HelpView(APIView):
    """
    An endpoint that returns a list of help menu items for the main navigation.
    Each menu item consists of a label (Markdown), url, icon (Font Awesome class, optional), image url (optional) and
    badge (optional).
    """

    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": [
                        {
                            "icon": "fa-question-circle",
                            "label": "<b>FAQ</b> (Frequently asked questions)",
                            "url": "https://localhost:8000/cms/faq/",
                            "is_external": True,
                            "image": None
                        },
                        {
                            "icon": "fa-life-ring",
                            "label": "<b>Support-Channel</b> (Chat)",
                            "url": "https://localhost:8000/cms/support/",
                            "is_external": True,
                            "image": None
                        }
                    ],
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        help_items = [
            MenuItem(label, url, icon, is_external=True)
            for label, url, icon in settings.COSINNUS_V3_MENU_HELP_LINKS
        ]
        return Response(help_items)


class ProfileView(APIView):
    """
    An endpoint that provides user profile menu items for the main navigation.
    Returns a list of menu items for user profile and notification settings, contribution, administration, logout and a
    language switcher item. The language switcher item contains a list of menu items for the available languages.
    Each menu item consists of a label (Markdown), url, icon (Font Awesome class, optional), image url (optional) and
    badge (optional).
    """

    permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": [
                        {
                            "icon": "fa-circle-user",
                            "label": "My Profile",
                            "url": "/profile/",
                            "image": None
                        },
                        {
                            "icon": "fa-language",
                            "label": "Change Language",
                            "url": None,
                            "image": None,
                            "sub_items": [
                                {
                                    "icon": None,
                                    "label": "Deutsch",
                                    "url": "/language/de/",
                                    "image": None
                                },
                                {
                                    "icon": None,
                                    "label": "English",
                                    "url": "/language/en/",
                                    "image": None
                                }
                            ]
                        }
                    ],
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        profile_menu = []

        # profile page
        profile_menu_items = [
            MenuItem(_('My Profile'), reverse('cosinnus:profile-detail'), 'fa-circle-user'),
        ]
        if settings.COSINNUS_V3_FRONTEND_ENABLED:
            profile_menu_items.append(
                MenuItem(_('Set up my Profile'), reverse('cosinnus:v3-frontend-setup-profile'), 'fa-pen'),
            )
        profile_menu_items.extend([
            MenuItem(_('Edit my Profile'), reverse('cosinnus:profile-edit'), 'fa-gear'),
            MenuItem(_('Notification Preferences'), reverse('cosinnus:notifications'), 'fa-envelope'),

        ])
        profile_menu.extend(profile_menu_items)

        # language
        if not settings.COSINNUS_LANGUAGE_SELECT_DISABLED:
            language_item = MenuItem(_('Change Language'), None, 'fa-language')
            language_subitems = [
                MenuItem(language, reverse('cosinnus:switch-language', kwargs={'language': code}))
                for code, language in settings.LANGUAGES
            ]
            language_item['sub_items'] = language_subitems
            profile_menu.append(language_item)

        # payments
        if settings.COSINNUS_PAYMENTS_ENABLED or settings.COSINNUS_PAYMENTS_ENABLED_ADMIN_ONLY \
                and request.user.is_superuser:
            from wechange_payments.models import Subscription
            current_subscription = Subscription.get_current_for_user(request.user)
            contribution = int(current_subscription.amount) if current_subscription else 0
            contribution_badge = f'{contribution} €'
            payments_item = MenuItem(_('Your Contribution'), reverse('wechange-payments:overview'),
                                     'fa-hand-holding-hart', badge=contribution_badge)
            profile_menu.append(payments_item)

        # administration
        if request.user.is_superuser or check_user_portal_manager(request.user):
            administration_item = MenuItem(
                _('Administration'), reverse('cosinnus:administration'), 'fa-screwdriver-wrench'
            )
            profile_menu.append(administration_item)

        # logout
        logout_item = MenuItem(_('Logout'), reverse('logout'), 'fa-right-from-bracket')
        profile_menu.append(logout_item)

        return Response(profile_menu)
