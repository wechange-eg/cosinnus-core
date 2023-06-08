from annoying.functions import get_object_or_None
from django.db.models import Case, Count, When
from django.urls.base import reverse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
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
from cosinnus.utils.permissions import check_user_can_create_conferences, check_user_can_create_groups
from cosinnus.utils.user import get_unread_message_count_for_user
from cosinnus.views.user_dashboard import MyGroupsClusteredMixin
from cosinnus_notifications.models import NotificationAlert


class SpacesView(MyGroupsClusteredMixin, APIView):
    """ An endpoint that returns the user spaces for the main navigation. """
    # TODO: Make names translateble, consider adding to cosinnus.trans.group.
    # TODO: Allow to configure community space names, e.g. using "discover" instead of "map".

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
                                    "image": None,
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
                                    "image": None,
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
            'Personal Dashboard', reverse('cosinnus:user-dashboard'), 'fa-user',
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
        if check_user_can_create_groups(request.user):
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
                community_space_items.append(
                    MenuItem('Forum', forum_group.get_absolute_url(), 'fa-sitemap')
                )
        community_space_items.append(MenuItem('Map', reverse('cosinnus:map'), 'fa-group'))
        community_space = {
            'items': community_space_items,
            'actions': [],
        }
        spaces['community'] = community_space

        # conferences
        if settings.COSINNUS_CONFERENCES_ENABLED:
            conferences = CosinnusConference.objects.get_for_user(request.user)
            conference_space_actions = []
            if check_user_can_create_conferences(request.user):
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
    """ An endpoint that returns the user bookmarks for the main navigation. """

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
                                "image": None,
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
    """ An endpoint that returns the user unread messages for the main navigation. """

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
    """ An endpoint that returns the user unseen alerts for the main navigation. """

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
