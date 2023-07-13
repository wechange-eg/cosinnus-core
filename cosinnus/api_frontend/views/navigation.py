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
from cosinnus.models.group import get_cosinnus_group_model, CosinnusPortal
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
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional) and image url (optional).
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
                                    "url": "http://localhost:8000/dashboard/",
                                    "image": "http://localhost:8000/media/cosinnus_portals/portal_default/avatars/user/0e9e945efe3d60bf807d56e336b677f193675fd8.png",
                                }
                            ],
                            "actions": []
                        },
                        "groups": {
                            "items": [
                                {
                                    "icon": "fa-sitemap",
                                    "label": "Test Group",
                                    "url": "http://localhost:8000/group/test-group/",
                                    "image": "http://localhost:8000/media/cosinnus_portals/portal_default/avatars/group/be5636c7955c1fd370514c26ffd4b0902dd5232a.png",
                                }
                            ],
                            "actions": [
                                {
                                    "icon": None,
                                    "label": "Create a Group",
                                    "url": "http://localhost:8000/groups/add/",
                                    "image": None,
                                },
                                {
                                    "icon": None,
                                    "label": "Create a Project",
                                    "url": "http://localhost:8000/projects/add/",
                                    "image": None,
                                }
                            ]
                        },
                        "community": {
                            "items": [
                                {
                                    "icon": "fa-sitemap",
                                    "label": "Forum",
                                    "url": "http://localhost:8000/group/forum/",
                                    "image": None,
                                },
                                {
                                    "icon": "fa-group",
                                    "label": "Map",
                                    "url": "http://localhost:8000/map/",
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
                                    "url": "http://localhost:8000/conference/test-conference/",
                                    "image": None,
                                }
                            ],
                            "actions": [
                                {
                                    "icon": None,
                                    "label": "Create a Conference",
                                    "url": "http://localhost:8000/conferences/add/",
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
            if forum_group and settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL:
                community_space_items.append(
                    MenuItem(settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL, forum_group.get_absolute_url(), 'fa-sitemap')
                )
        if settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL:
            community_space_items.append(
                MenuItem(settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL, reverse('cosinnus:map'), 'fa-group')
            )
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
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional) and image url (optional).
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
                                "url": "http://localhost:8000/group/test-group/",
                                "image": "http://localhost:8000/media/cosinnus_portals/portal_default/avatars/group/be5636c7955c1fd370514c26ffd4b0902dd5232a.png",
                            }
                        ],
                        "users": [
                            {
                                "icon": "fa-user",
                                "label": "Test User",
                                "url": "http://localhost:8000/user/2/",
                                "image": None,
                            }
                        ],
                        "content": [
                            {
                                "icon": "fa-lightbulb-o",
                                "label": "Test Idea",
                                "url": "http://localhost:8000/map/?item=1.ideas.test-idea",
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
    Returns a list of alert items, consisting of a text (label), url, icon_or_image_url, action_datetime and additional
    alert details. Unread alerts are marked via "is_emphasized".

    Multiple related alerts are bundled in a single alert item as sub_items:
    - is_multi_user_alert: is for events happening on a single content object, but with multiple users acting on it.
    - is_bundle_alert: is a single alert object bundled for multiple content objects causing events in a short
      time frame, all by the same user in the same group.

    Each sub alert contains text (label), url and icon_or_image_url elements.
    The response list is paginated by 10 items. For pagination the "offset_timestamp" parameter should be used.
    To receive new alerts the "newer_than_timestamp" should be used.
    """
    # TODO: consider caching.
    # TODO: discuss pagination, newer_than_timestamp, offset_timestamp.
    # TODO: discuss limiting the fields to data needed by the frontend.

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
                                "url": "http://localhost:8000/group/test-group/members/",
                                "item_icon_or_image_url": "fa-sitemap",
                                "user_icon_or_image_url": "/static/images/jane-doe-small.png",
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
                                "url": "http://localhost:8000/group/test-project/members/",
                                "item_icon_or_image_url": "fa-group",
                                "user_icon_or_image_url": "/static/images/jane-doe-small.png",
                                "group": "Test Project",
                                "group_icon": "fa-group",
                                "action_datetime": "2023-05-20T16:04:36.501003+00:00",
                                "is_emphasized": False,
                                "alert_reason": "You are an admin of this team",
                                "sub_items": [
                                    {
                                        "title": "User 3",
                                        "url": "http://localhost:8000/user/4/",
                                        "icon_or_image_url": "/static/images/jane-doe-small.png"
                                    },
                                    {
                                        "title": "User 4",
                                        "url": "http://localhost:8000/user/5/",
                                        "icon_or_image_url": "/static/images/jane-doe-small.png"
                                    }
                                ],
                                "is_multi_user_alert": True,
                                "is_bundle_alert": False
                            },
                            {
                                "text": "<b>User 2</b> created 2 news posts.",
                                "id": 1,
                                "url": "http://localhost:8000/group/test-group/note/1401481714/",
                                "item_icon_or_image_url": "fa-quote-right",
                                "user_icon_or_image_url": "/static/images/jane-doe-small.png",
                                "group": "Test Group",
                                "group_icon": "fa-sitemap",
                                "action_datetime": "2023-05-24T08:44:50.570918+00:00",
                                "is_emphasized": True,
                                "alert_reason": "You are following this content or its Project or Group",
                                "sub_items": [
                                    {
                                        "title": "test2",
                                        "url": "http://localhost:8000/group/test-group/note/1455745550/",
                                        "icon_or_image_url": "fa-quote-right"
                                    },
                                    {
                                        "title": "test",
                                        "url": "http://localhost:8000/group/test-group/note/1401481714/",
                                        "icon_or_image_url": "fa-quote-right"
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

        # alert items
        user_cache = self.get_user_cache(alerts)
        items = [
            SerializedNotificationAlert(
                alert,
                action_user=user_cache[alert.action_user_id][0],
                action_user_profile=user_cache[alert.action_user_id][1],
            ) for alert in alerts
        ]
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


class HelpView(APIView):
    """
    An endpoint that returns a list of help menu items for the main navigation.
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional) and image url (optional).
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
                            "url": "https://localhost:8000/faq/",
                            "image": None
                        },
                        {
                            "icon": "fa-life-ring",
                            "label": "<b>Support-Channel</b> (Chat)",
                            "url": "https://localhost:8000/support/",
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
        help_items = [MenuItem(label, url, icon) for label, url, icon in settings.COSINNUS_V3_MENU_HELP_LINKS]
        return Response(help_items)


class ProfileView(APIView):
    """
    An endpoint that provides user profile menu items for the main navigation.
    Returns a list of menu items for user profile and notification settings, contribution, administration, logout and a
    language switcher item. The language switcher item contains a list of menu items for the available languages.
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional) and image url (optional).
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
                            "url": "http://localhost:8000/profile/",
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
                                    "url": "http://localhost:8000/language/de/",
                                    "image": None
                                },
                                {
                                    "icon": None,
                                    "label": "English",
                                    "url": "http://localhost:8000/language/en/",
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
        # TODO: consider my_contribution_badge
        if settings.COSINNUS_PAYMENTS_ENABLED or settings.COSINNUS_PAYMENTS_ENABLED_ADMIN_ONLY \
                and request.user.is_superuser:
            payments_item = MenuItem(_('Your Contribution'), reverse('wechange-payments:overview'), 'fa-hand-holding-hart')
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
