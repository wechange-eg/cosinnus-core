from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model
from django.db.models import Case, Count, When
from django.urls.base import reverse
from django.utils.translation import ugettext_lazy as _
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
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional), image url (optional) and
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
                    "data": {
                        "personal": {
                            "items": [
                                MenuItem("Personal Dashboard", "/dashboard/", "fa-user", "/media/image.png",
                                         id="PersonalDashboard"),
                            ],
                            "actions": []
                        },
                        "groups": {
                            "items": [
                                MenuItem("Test Group", "/group/test-group/", "fa-sitemap", "/media/image.png",
                                         id="CosinnusSociety70")
                            ],
                            "actions": [
                                MenuItem("Create a Group", "/groups/add/", id="CreateGroup"),
                                MenuItem("Create a Project", "/projects/add/", id="CreateProject"),
                            ]
                        },
                        "community": {
                            "items": [
                                MenuItem("Forum", "/group/forum/", "fa-sitemap", id="Forum"),
                                MenuItem("Map", "/map/", "fa-group", id="Map"),
                            ],
                            "actions": []
                        },
                        "conference": {
                            "items": [
                                MenuItem("Test Conference", "/conference/test-conference/", "fa-television", id="CosinnusSociety70"),
                            ],
                            "actions": [
                                MenuItem("Create a Conference", "/conferences/add/", id="CreateConference"),
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
        personal_space = None
        if request.user.is_authenticated:
            personal_space_items = [
                MenuItem(
                    _('Personal Dashboard'), reverse('cosinnus:user-dashboard'), 'fa-user',
                    request.user.cosinnus_profile.avatar_url, id='PersonalDashboard',
                )
            ]
            personal_space = {
                'items': personal_space_items,
                'actions': [],
            }
        spaces['personal'] = personal_space

        # projects and groups
        group_space_items = []
        group_space_actions = []
        if request.user.is_authenticated:
            group_space_items = [
                dashboard_item.as_menu_item()
                for cluster in self.get_group_clusters(request.user) for dashboard_item in cluster
            ]
        if not settings.COSINNUS_SHOW_MAIN_MENU_GROUP_CREATE_BUTTON_ONLY_FOR_PERMITTED \
                or check_user_can_create_groups(request.user):
            group_space_actions = [
                MenuItem(CosinnusSocietyTrans.CREATE_NEW, reverse('cosinnus:group__group-add'), id="CreateGroup"),
                MenuItem(CosinnusProjectTrans.CREATE_NEW, reverse('cosinnus:group-add'), id="CreateProject"),
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
            forum_group = get_object_or_None(get_cosinnus_group_model(), slug=forum_slug,
                                             portal=CosinnusPortal.get_current())
            if forum_group:
                if (settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_LINKS_FROM_MANAGED_TAG_GROUPS
                        and request.user.is_authenticated):
                    # Add paired_groups of managed tags to community space.
                    managed_tags = self.request.user.cosinnus_profile.get_managed_tags()
                    if managed_tags:
                        for tag in managed_tags:
                            if tag.paired_group and tag.paired_group != forum_group:
                                community_space_items.append(
                                    MenuItem(tag.paired_group.name, tag.paired_group.get_absolute_url(),
                                             'fa-group', id=f'Forum{tag.paired_group.id}')
                                )
                if settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL:
                    community_space_items.append(
                        MenuItem(settings.COSINNUS_V3_MENU_SPACES_FORUM_LABEL, forum_group.get_absolute_url(),
                                 'fa-sitemap', id='Forum')
                    )
        if settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL:
            community_space_items.append(
                MenuItem(settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL, reverse('cosinnus:map'), 'fa-group', id='Map')
            )
        if settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS:
            community_space_items.extend([
                MenuItem(label, url, icon, id=id)
                for id, label, url, icon in settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS
            ])
        community_space = {
            'items': community_space_items,
            'actions': [],
        }
        spaces['community'] = community_space

        # conferences
        if settings.COSINNUS_CONFERENCES_ENABLED:
            conference_space_items = []
            conference_space_actions = []
            if request.user.is_authenticated:
                conferences = CosinnusConference.objects.get_for_user(request.user)
                conference_space_items = [DashboardItem(conference).as_menu_item() for conference in conferences]
            if not settings.COSINNUS_SHOW_MAIN_MENU_CONFERENCE_CREATE_BUTTON_ONLY_FOR_PERMITTED \
                    or check_user_can_create_conferences(request.user):
                conference_space_actions = [
                    MenuItem(CosinnusConferenceTrans.CREATE_NEW, reverse('cosinnus:conference__group-add'),
                             id='CreateConference'),
                ]
            conference_space = {
                'items': conference_space_items,
                'actions': conference_space_actions,
            }
            spaces['conference'] = conference_space

        return Response(spaces)


class BookmarksView(APIView):
    """
    An endpoint that provides the user bookmarks for the main navigation.
    Returns menu items for liked groups and projects, liked users and liked content (e.g. ideas).
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional), image url (optional) and
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
                    "data": {
                        "groups": [
                            MenuItem("Test Group", "/group/test-group/", "fa-sitemap", "/media/image.png",
                                     id="CosinnusGroup70"),
                        ],
                        "users": [
                            MenuItem("Test User", "/user/2/", "fa-user", id="UserProfile4"),
                        ],
                        "content": [
                            MenuItem("Test Idea", "/map/?item=1.ideas.test-idea", "fa-lightbulb-o", id="CosinnusIdea2"),
                        ]
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        bookmarks = {}
        group_items = []
        content_items = []
        if request.user.is_authenticated:
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
                    'groups': group_items,
                    'users': user_items,
                    'content': content_items,
                }
        return Response(bookmarks)


class UnreadMessagesView(APIView):
    """ An endpoint that returns the user unread message count for the main navigation. """

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
        unread_message_count = 0
        if request.user.is_authenticated:
            unread_message_count = get_unread_message_count_for_user(request.user)
        unread_messages = {
            'count': unread_message_count,
        }
        return Response(unread_messages)


class UnreadAlertsView(APIView):
    """ An endpoint that returns the user unseen alerts count for the main navigation. """

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
        alerts_count = 0
        if request.user.is_authenticated:
            alerts_qs = NotificationAlert.objects.filter(portal=CosinnusPortal.get_current(), user=self.request.user)
            unseen_aggr = alerts_qs.aggregate(seen_count=Count(Case(When(seen=False, then=1))))
            alerts_count = unseen_aggr.get('seen_count', 0)
        unread_alerts = {
            'count': alerts_count
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
                                "id": "Alert3",
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
                                "id": "Alert2",
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
                                "id": "Alert1",
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
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional), image url (optional) and
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
                        MenuItem("<b>FAQ</b> (Frequently asked questions)", "https://localhost/cms/faq/",
                                 "fa-question-circle", is_external=True, id="FAQ"),
                        MenuItem("<b>Support-Channel</b> (Chat)", "https://localhost/cms/support/",
                                 "fa-life-ring", is_external=True, id="Support"),
                    ],
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
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
        language_selection = filter(lambda l: l[0] in settings.COSINNUS_V3_FRONTEND_SUPPORTED_LANGUAGES,
                                    settings.LANGUAGES)
        language_subitems = []
        for code, language in language_selection:
            language_subitem = MenuItem(language, reverse('cosinnus:switch-language', kwargs={'language': code}),
                                        id=f'ChangeLanguageItem{code.upper()}')
            language_subitem['selected'] = code == request.LANGUAGE_CODE
            language_subitems.append(language_subitem)
        language_item['sub_items'] = language_subitems
        return language_item


class ProfileView(LanguageMenuItemMixin, APIView):
    """
    An endpoint that provides user profile menu items for the main navigation.
    Returns a list of menu items for user profile and notification settings, contribution, administration, logout and a
    language switcher item. The language switcher item contains a list of menu items for the available languages.
    Each menu item consists of a label (HTML), url, icon (Font Awesome class, optional), image url (optional) and
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
                        MenuItem("My Profile", "/profile/", "fa-circle-user", id="Profile"),
                        MenuItem("Set up my Profile", "/profile/edit/", "fa-pen", id="SetupProfile"),
                        MenuItem("Edit my Profile", "/profile/edit/", "fa-gear", id="EditProfile"),
                        MenuItem("Notification Preferences", "/profile/notifications/", "fa-envelope",
                                 id="NotificationPreferences"),
                        {
                            "id": "ChangeLanguage",
                            "icon": "fa-language",
                            "label": "Change Language",
                            "url": None,
                            "image": None,
                            "is_external": False,
                            "badge": None,
                            "sub_items": [
                                {
                                    "id": "ChangeLanguageItemDE",
                                    "icon": None,
                                    "label": "Deutsch",
                                    "url": "/language/de/",
                                    "image": None,
                                    "is_external": False,
                                    "badge": None,
                                },
                                {
                                    "id": "ChangeLanguageItemEN",
                                    "icon": None,
                                    "label": "English",
                                    "url": "/language/en/",
                                    "image": None,
                                    "is_external": False,
                                    "badge": None,
                                },
                            ],
                        },
                        MenuItem("Your Contribution", "/account/contribution/", "fa-hand-holding-hart",
                                 id="Contribution"),
                        MenuItem("Logout", "/logout/", "fa-right-from-bracket", id="Logout"),
                    ],
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        profile_menu = []

        if request.user.is_authenticated:
            # profile page
            profile_menu_items = [
                MenuItem(_('My Profile'), reverse('cosinnus:profile-detail'), 'fa-circle-user', id='Profile'),
            ]
            if settings.COSINNUS_V3_FRONTEND_ENABLED:
                profile_menu_items.append(
                    MenuItem(_('Set up my Profile'), reverse('cosinnus:v3-frontend-setup-profile'), 'fa-pen',
                             id='SetupProfile'),
                )
            profile_menu_items.extend([
                MenuItem(_('Edit my Profile'), reverse('cosinnus:profile-edit'), 'fa-gear', id='EditProfile'),
                MenuItem(_('Notification Preferences'), reverse('cosinnus:notifications'), 'fa-envelope',
                         id='NotificationPreferences'),

            ])
            profile_menu.extend(profile_menu_items)

            # language
            if not settings.COSINNUS_LANGUAGE_SELECT_DISABLED:
                language_item = self.get_language_menu_item(request)
                profile_menu.append(language_item)

            # payments
            if settings.COSINNUS_PAYMENTS_ENABLED or settings.COSINNUS_PAYMENTS_ENABLED_ADMIN_ONLY \
                    and request.user.is_superuser:
                from wechange_payments.models import Subscription
                current_subscription = Subscription.get_current_for_user(request.user)
                contribution = int(current_subscription.amount) if current_subscription else 0
                contribution_badge = f'{contribution} €'
                payments_item = MenuItem(_('Your Contribution'), reverse('wechange-payments:overview'),
                                         'fa-hand-holding-hart', badge=contribution_badge, id='Contribution')
                profile_menu.append(payments_item)

            # administration
            if request.user.is_superuser or check_user_portal_manager(request.user):
                administration_item = MenuItem(_('Administration'), reverse('cosinnus:administration'),
                                               'fa-screwdriver-wrench', id='Administration')
                profile_menu.append(administration_item)

            # logout
            logout_item = MenuItem(_('Logout'), reverse('logout'), 'fa-right-from-bracket', id='Logout')
            profile_menu.append(logout_item)

        return Response(profile_menu)


class MainNavigationView(LanguageMenuItemMixin, APIView):
    """
    An endpoint that provides menu items for main navigation.
    It contains pseudo menu items just to indicate the availability of a menu-item (e.g. for spaces and search) or
    actual menu items (e.g. cloud, login). The content of the main navigation differs for authenticated and
    non-authenticated users.
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
                    "data": {
                        'left': [
                            MenuItem("Home", "/cms/?noredir=1", image='/static/img/logo-icon.png', id='Home'),
                            MenuItem("Spaces", id="Spaces"),
                        ],
                        'middle': [
                            MenuItem("Search", "/search/", "fa-magnifying-glass", id="Search"),
                            MenuItem("Bookmarks", icon="fa-bookmark", id="Bookmarks"),
                        ],
                        'services': [
                            MenuItem("Cloud", "https://cloud.localhost/", "fa-cloud", is_external=True, id="Cloud"),
                            MenuItem("Rocket.Chat", "/messages/", "fa-envelope", id="Chat"),
                        ],
                        'right': [
                            MenuItem("Help", icon="fa-question", id="Help"),
                            MenuItem("Alerts", icon="fa-bell", id="Alerts"),
                            MenuItem("Profile", icon="fa-user", id="Profile"),
                        ]
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
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
        home_image = current_portal.get_logo_image_url()
        if settings.COSINNUS_V3_MENU_HOME_LINK:
            home_item = MenuItem(_('Home'), settings.COSINNUS_V3_MENU_HOME_LINK, icon='fa-home', image=home_image,
                                 id='Home')
        else:
            home_item = MenuItem(_('Dashboard'), reverse('cosinnus:user-dashboard'), icon='fa-home', image=home_image,
                                 id='HomeDashboard')
        left_navigation_items.append(home_item)

        # spaces
        left_navigation_items.append(MenuItem('Spaces', id='Spaces'))

        main_navigation_items['left'] = left_navigation_items

        # middle part
        middle_navigation_items = []

        # search
        if request.user.is_authenticated:
            search_item = MenuItem(_('Search'), reverse('cosinnus:search'), 'fa-magnifying-glass', id='Search')
        else:
            search_item = MenuItem(_('Search'), reverse('cosinnus:map'), 'fa-magnifying-glass', id='MapSearch')
        middle_navigation_items.append(search_item)

        if request.user.is_authenticated:
            # bookmarks
            middle_navigation_items.append(MenuItem(_('Bookmarks'), icon='fa-bookmark', id='Bookmarks'))

        main_navigation_items['middle'] = middle_navigation_items

        # services part
        services_navigation_items = []

        if request.user.is_authenticated:
            # cloud
            if settings.COSINNUS_CLOUD_ENABLED:
                services_navigation_items.append(
                    MenuItem(_('Cloud'), settings.COSINNUS_CLOUD_NEXTCLOUD_URL, icon='fa-cloud',
                             is_external=settings.COSINNUS_CLOUD_OPEN_IN_NEW_TAB, id='Cloud')
                )

            # messages
            if 'cosinnus_message' not in settings.COSINNUS_DISABLED_COSINNUS_APPS:
                if settings.COSINNUS_ROCKET_ENABLED:
                    services_navigation_items.append(
                        MenuItem('Rocket.Chat', reverse('cosinnus:message-global'), icon='fa-envelope',
                                 is_external=settings.COSINNUS_ROCKET_OPEN_IN_NEW_TAB, id='Chat')
                    )
                else:
                    services_navigation_items.append(
                        MenuItem( _('Messages'), reverse('postman:inbox'), icon='fa-envelope', id='Messages')
                    )
        main_navigation_items['services'] = services_navigation_items

        # right part
        right_navigation_items = []

        # help
        right_navigation_items.append(MenuItem(_('Help'), icon='fa-question', id='Help'))

        if request.user.is_authenticated:

            # alerts
            right_navigation_items.append(MenuItem(_('Alerts'), icon='fa-bell', id='Alerts'))

            # profile
            right_navigation_items.append(MenuItem(_('Profile'), icon='fa-user', id='Profile'))
        else:

            # language
            if not settings.COSINNUS_LANGUAGE_SELECT_DISABLED:
                language_item = self.get_language_menu_item(request, current_language_as_label=True)
                right_navigation_items.append(language_item)

            # login
            right_navigation_items.append(MenuItem(_('Login'), reverse('login'), id='Login'))

            # register
            if settings.COSINNUS_USER_SIGNUP_ENABLED:
                right_navigation_items.append(
                    MenuItem(_('Register'), reverse('cosinnus:user-add'),  id='Register')
                )

        main_navigation_items['right'] = right_navigation_items

        return Response(main_navigation_items)
