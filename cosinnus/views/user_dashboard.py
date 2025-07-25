# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import itertools
import json
import logging
import math
from datetime import timedelta

import six
from annoying.functions import get_object_or_None
from dateutil.relativedelta import relativedelta
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.http.response import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.views.generic import TemplateView
from django.views.generic.base import View

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusGroupMembership, CosinnusPortal
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.map import SEARCH_MODEL_NAMES_REVERSE
from cosinnus.models.membership import MEMBER_STATUS
from cosinnus.models.tagged import (
    BaseHierarchicalTaggableObjectModel,
    BaseTaggableObjectModel,
    BaseTagObject,
    LastVisitedObject,
    LikeObject,
)
from cosinnus.models.user_dashboard import DashboardItem
from cosinnus.models.user_dashboard_announcement import UserDashboardAnnouncement
from cosinnus.utils.dates import datetime_from_timestamp, timestamp_from_datetime
from cosinnus.utils.filters import exclude_special_folders
from cosinnus.utils.functions import is_number, sort_key_strcoll_attr
from cosinnus.utils.group import get_cosinnus_group_model, get_default_user_group_slugs
from cosinnus.utils.pagination import QuerysetLazyCombiner
from cosinnus.utils.permissions import (
    check_user_superuser,
    filter_base_taggable_qs_for_blocked_user_content,
    filter_tagged_object_queryset_for_user,
)
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.mixins.group import RequireLoggedInMixin
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from cosinnus.views.ui_prefs import get_ui_prefs_for_user

logger = logging.getLogger('cosinnus')


class UserDashboardView(RequireLoggedInMixin, TemplateView):
    template_name = 'cosinnus/v2/dashboard/user_dashboard.html'

    def get(self, request, *args, **kwargs):
        if not (
            getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False)
            or (getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False) and request.user.is_superuser)
        ):
            return redirect('cosinnus:map')
        # disable dashboard for user but instead redirect them to their linked group
        if request.user.is_authenticated and request.user.is_guest:
            return redirect(
                group_aware_reverse(
                    'cosinnus:group-dashboard',
                    kwargs={'group': request.user.cosinnus_profile.guest_access_object.group},
                )
            )
        return super(UserDashboardView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.request.user
        forum_group = None
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        note_form = None
        if forum_slug:
            forum_group = get_object_or_None(
                get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current()
            )
            try:
                from cosinnus_note.forms import NoteForm

                note_form = NoteForm(group=forum_group)
            except Exception:
                if settings.DEBUG:
                    raise

        announcement = None
        announcement_is_preview = False
        # for superusers, check if we're viewing an announcement_preview
        if self.request.GET.get('show_announcement', None) is not None and check_user_superuser(user):
            announcement_id = self.request.GET.get('show_announcement')
            if is_number(announcement_id):
                announcement_is_preview = True
                announcement = get_object_or_None(UserDashboardAnnouncement, id=int(announcement_id))
        else:
            announcement = UserDashboardAnnouncement.get_next_for_user(user)

        welcome_screen_expired = user.date_joined < (
            now() - timedelta(days=getattr(settings, 'COSINNUS_V2_DASHBOARD_WELCOME_SCREEN_EXPIRY_DAYS', 7))
        )
        welcome_screen_enabled = getattr(settings, 'COSINNUS_V2_DASHBOARD_WELCOME_SCREEN_ENABLED', True)

        options = {
            'ui_prefs': get_ui_prefs_for_user(user),
            'force_only_mine': getattr(settings, 'COSINNUS_USERDASHBOARD_FORCE_ONLY_MINE', False)
            or getattr(settings, 'COSINNUS_FORUM_DISABLED', False),
        }
        ctx = {
            'user_dashboard_options_json': json.dumps(options),
            'forum_group': forum_group,
            'note_form': note_form,
            'announcement': announcement,
            'announcement_is_preview': announcement_is_preview,
            'show_welcome_screen': welcome_screen_enabled and not welcome_screen_expired,
        }
        _now = now()
        attending_events = []
        try:
            from cosinnus_event.models import Event, EventAttendance  # noqa

            my_attendances_ids = EventAttendance.objects.filter(
                user=user, state__gt=EventAttendance.ATTENDANCE_NOT_GOING
            ).values_list('event_id', flat=True)
            attending_events = Event.get_current_for_portal().filter(id__in=my_attendances_ids)
            attending_events = filter_tagged_object_queryset_for_user(attending_events, user)
        except Exception:
            if settings.DEBUG:
                raise
        if attending_events:
            ctx['attending_events'] = attending_events

        if settings.COSINNUS_CONFERENCES_ENABLED:
            my_conferences = CosinnusConference.objects.get_for_user(user)
            my_current_conferences = [
                (conf, conf.get_icon())
                for conf in my_conferences
                if conf.get_or_infer_to_date and conf.get_or_infer_to_date > _now
            ]
            my_pending_conference_applications = [
                (appl.conference, appl.get_icon()) for appl in user.user_applications.pending_current()
            ]
            ctx['my_upcoming_conferences_with_icons'] = my_pending_conference_applications + my_current_conferences
        return ctx


user_dashboard_view = UserDashboardView.as_view()


class BaseUserDashboardWidgetView(View):
    http_method_names = [
        'get',
    ]

    def get(self, request, *args, **kwargs):
        # require authenticated user
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated.')

        response = {
            'data': self.get_data(**kwargs),
        }
        return JsonResponse(response)


class MyGroupsClusteredMixin(object):
    def get_group_clusters(self, user, sort_by_activity=False):
        clusters = []

        # collect map of last visited groups
        group_ct = ContentType.objects.get_for_model(get_cosinnus_group_model())
        if sort_by_activity:
            group_last_visited_qs = LastVisitedObject.objects.filter(
                user=user, content_type=group_ct, portal=CosinnusPortal.get_current()
            )
            # a dict of group-id -> datetime
            group_last_visited = dict(group_last_visited_qs.values_list('object_id', 'visited'))
        else:
            group_last_visited = {}
        default_date = now() - relativedelta(years=100)

        # collect and sort user projects and societies lists
        projects = list(CosinnusProject.objects.get_for_user(user))
        societies = list(CosinnusSociety.objects.get_for_user(user))
        # sort sub items by last_visited or name
        if sort_by_activity:
            projects = sorted(
                projects, key=lambda project: group_last_visited.get(project.id, default_date), reverse=True
            )
            societies = sorted(
                societies, key=lambda society: group_last_visited.get(society.id, default_date), reverse=True
            )
        else:
            projects = sorted(projects, key=sort_key_strcoll_attr('name'))
            societies = sorted(societies, key=sort_key_strcoll_attr('name'))

        # sort projects into their societies clusters, society clusters are always displayed first
        for society in societies:
            if society.slug in get_default_user_group_slugs():
                continue

            # if enabled in v3 the managed tags groups are part of community spaces and can be skipped
            if (
                settings.COSINNUS_V3_FRONTEND_ENABLED
                and settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_LINKS_FROM_MANAGED_TAG_GROUPS
            ):
                managed_tags = user.cosinnus_profile.get_managed_tags()
                paired_groups = [tag.paired_group for tag in managed_tags if tag.paired_group]
                if society in paired_groups:
                    continue

            # the most recent visit time to any project or society in the cluster
            most_recent_dt = group_last_visited.get(society.id, default_date)
            items_projects = []
            for i in range(len(projects) - 1, -1, -1):
                project = projects[i]
                if project.parent == society:
                    items_projects.insert(0, DashboardItem(project))  # prepend because of reversed order
                    projects.pop(i)
                    project_dt = group_last_visited.get(project.id, default_date)
                    most_recent_dt = project_dt if project_dt > most_recent_dt else most_recent_dt
            items = [DashboardItem(society, is_emphasized=True)] + items_projects
            clusters.append(items)

        # add unclustered projects as own cluster
        for proj in projects:
            items = [DashboardItem(proj)]
            clusters.append(items)

        return clusters


class GroupWidgetView(MyGroupsClusteredMixin, BaseUserDashboardWidgetView):
    """Shows (for now) unlimited, all projects clustered by groups of a user.
    TODO: implement sorting by last accessed
    TODO: implement limiting to 3 projects per group and n total items.
    TODO: use clever caching"""

    def get_data(self, *kwargs):
        clusters = self.get_group_clusters(self.request.user, sort_by_activity=True)
        return {'group_clusters': clusters}


api_user_groups = GroupWidgetView.as_view()


class LikedIdeasWidgetView(BaseUserDashboardWidgetView):
    """Shows all unlimited (for now) ideas the user likes."""

    def get_data(self, *kwargs):
        idea_ct = ContentType.objects.get_for_model(CosinnusIdea)
        likeobjects = LikeObject.objects.filter(user=self.request.user, content_type=idea_ct, liked=True)
        liked_ideas_ids = likeobjects.values_list('object_id', flat=True)
        liked_ideas = CosinnusIdea.objects.all_in_portal().filter(id__in=liked_ideas_ids)
        ideas = [DashboardItem(idea) for idea in liked_ideas]
        return {'items': ideas}


api_user_liked_ideas = LikedIdeasWidgetView.as_view()


class StarredUsersWidgetView(BaseUserDashboardWidgetView):
    """Shows all unlimited (for now) ideas the user likes."""

    def get_data(self, *kwargs):
        liked_users = self.request.user.cosinnus_profile.get_user_starred_users()
        users = []
        for user in liked_users:
            dashboard_item = DashboardItem(user)
            dashboard_item['id'] = user.id
            dashboard_item['ct'] = user.get_content_type()
            users.append(dashboard_item)
        return {'items': users}


api_user_starred_users = StarredUsersWidgetView.as_view()


class StarredObjectsWidgetView(BaseUserDashboardWidgetView):
    """Shows all unlimited (for now) ideas the user likes."""

    def get_data(self, *kwargs):
        liked_objects = self.request.user.cosinnus_profile.get_user_starred_objects()
        objects = []
        for obj in liked_objects:
            dashboard_item = DashboardItem(obj)
            dashboard_item['id'] = obj.id
            dashboard_item['ct'] = obj.get_content_type()
            objects.append(dashboard_item)
        return {'items': objects}


api_user_starred_objects = StarredObjectsWidgetView.as_view()


class FollowedObjectsWidgetView(BaseUserDashboardWidgetView):
    """Shows all unlimited (for now) ideas the user likes."""

    def get_data(self, *kwargs):
        followed = LikeObject.objects.filter(user=self.request.user, followed=True)
        objects = []
        for follow in followed:
            ct = ContentType.objects.get_for_id(follow.content_type.id)
            model_class = ct.model_class()
            obj = get_object_or_None(model_class, pk=follow.object_id)
            # should the target object not exist, delete the follow relation
            if not obj:
                follow.delete()
                continue

            # filter inactive groups
            if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
                if not obj.is_active:
                    continue
            elif hasattr(obj, 'group'):
                # also filter inactive parent groups
                if not getattr(obj.group, 'is_active', False):
                    continue

            dashboard_item = DashboardItem(obj)
            dashboard_item['id'] = obj.id
            dashboard_item['ct'] = obj.get_content_type()
            objects.append(dashboard_item)
        return {'items': objects}


api_user_followed_objects = FollowedObjectsWidgetView.as_view()


class ModelRetrievalMixin(object):
    """Mixin for all dashboard views requiring content data"""

    def fetch_queryset_for_user(
        self,
        model,
        user,
        sort_key=None,
        only_mine=True,
        only_mine_strict=True,
        all_public=False,
        only_forum=False,
        current_only=True,
    ):
        """Retrieves a queryset of sorted content items for a user, for a given model.
        @param model: An actual model class. Supported are all `BaseTaggableObjectModel`s,
            `CosinnusIdea`, and `postman.Message`
        @param user: Querysets are filtered by view permission for this user
        @param sort_key: (optional) the key for the `order_by` clause for the queryset
        @param only_mine: if True, will only show objects that belong to groups or projects
            the `user` is a member of, including the Forum, and including Ideas.
            If False, will include all visible items in this portal for the user.
            This is basically an "exclude unrelated public items" switch.
        @param only_mine_strict: If set to True along with `only_mine`, really only objects
            from the user's groups and projects will be returned, *excluding* the Forum and
            Ideas.
            This is basically a switch to only return items that are relevant to ME because
            they are from groups/projects I am a member of voluntarily.
        @param all_public: if True, includes ALL content that is specifically set to public
            visibility. This will filter out any other content from groups, even if it would
            be visible for the current user normally. This clashes with `only_mine==True`, as it
            does not filter further down for the user's only items!
        @param only_forum: if True, includes only such items that are contained in groups
            that any user joins automatically, i.e. the forum/events group as configured
            per portal, and also Ideas as they are plattform wide.
        @param current_only: if True, will only retrieve current items (ie, upcoming events)
            TODO: is this correct?
        """

        ct = ContentType.objects.get_for_model(model)
        model_name = '%s.%s' % (ct.app_label, ct.model_class().__name__)

        # ideas are excluded in strict mode
        if model is CosinnusIdea and only_mine and only_mine_strict:
            return model.objects.none()

        queryset = None
        skip_filters = False
        if BaseHierarchicalTaggableObjectModel in inspect.getmro(model):
            queryset = model._default_manager.filter(is_container=False, group__is_active=True)
            queryset = exclude_special_folders(queryset)
        elif model_name == 'cosinnus_event.Event':
            if current_only:
                queryset = model.objects.all_upcoming()
            else:
                queryset = model.objects.get_queryset()
            queryset = queryset.exclude(is_hidden_group_proxy=True)
        elif model_name == 'cosinnus_marketplace.Offer':
            queryset = model.objects.all_active()
        elif model is CosinnusIdea:
            queryset = model._default_manager.all()
        elif BaseTaggableObjectModel in inspect.getmro(model):
            queryset = model._default_manager.all().filter(group__is_active=True)
        elif model_name == 'postman.Message':
            queryset = model.objects.inbox(user)
            skip_filters = True
        elif model is get_cosinnus_group_model() or issubclass(model, get_cosinnus_group_model()):
            queryset = model.objects.get_queryset().filter(is_active=True)
        else:
            return None

        assert queryset is not None
        if not skip_filters:
            # mix in reflected objects
            if (
                model_name.lower() in settings.COSINNUS_REFLECTABLE_OBJECTS
                and BaseTaggableObjectModel in inspect.getmro(model)
            ):
                mixin = MixReflectedObjectsMixin()
                queryset = mixin.mix_queryset(queryset, model, None, user)

            portal_id = CosinnusPortal.get_current().id
            portal_list = [portal_id]
            if False:
                # include all other portals in pool
                portal_list += getattr(settings, 'COSINNUS_SEARCH_DISPLAY_FOREIGN_PORTALS', [])

            if (
                model is CosinnusIdea
                or model is get_cosinnus_group_model()
                or issubclass(model, get_cosinnus_group_model())
            ):
                queryset = queryset.filter(portal__id__in=portal_list)
                # check if a group/project should appear in quicksearch results for anonymous users
                if (
                    model is get_cosinnus_group_model()
                    or issubclass(model, get_cosinnus_group_model())
                    and not user.is_authenticated
                ):
                    # if this portal cannot select the group visibility and the default is not visible, return no groups
                    if not settings.COSINNUS_GROUP_PUBLICY_VISIBLE_OPTION_SHOWN:
                        if settings.COSINNUS_GROUP_PUBLICLY_VISIBLE_DEFAULT_VALUE is False:
                            queryset = queryset.none()
                    else:
                        queryset = queryset.filter(publicly_visible=True)
                if all_public:
                    queryset = queryset.filter(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
            else:
                # filter for project and group content from within this portal (no conference contents!)
                dashboard_content_group_types = [
                    CosinnusProject.GROUP_MODEL_TYPE,
                    CosinnusSociety.GROUP_MODEL_TYPE,
                ]
                queryset = queryset.filter(
                    group__portal__id__in=portal_list, group__type__in=dashboard_content_group_types
                )

                if all_public:
                    # if include_only_public mode is on, do not filter on any groups specifically, but include
                    # everything that is tagged with public visibility
                    # might want to make `all_public` combinable with only_mine for clarity in the future...
                    filter_q = Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
                else:
                    user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(user)
                    default_user_group_slugs = get_default_user_group_slugs()
                    if default_user_group_slugs:
                        # in strict mode, filter any content from the default groups as well
                        default_user_groups = get_cosinnus_group_model().objects.get_cached(
                            slugs=default_user_group_slugs, portal_id=portal_id
                        )
                        default_user_group_ids = [group.id for group in default_user_groups]
                        if only_mine and only_mine_strict:
                            user_group_ids = [
                                group_id for group_id in user_group_ids if group_id not in default_user_group_ids
                            ]
                        elif only_forum:
                            # in specific forum mode, EXCLUDE any content NOT from the default groups
                            user_group_ids = [
                                group_id for group_id in user_group_ids if group_id in default_user_group_ids
                            ]
                    filter_q = Q(group__pk__in=user_group_ids)
                    # if the switch is on, also include public posts from all portals
                    if not only_mine and not only_forum:
                        filter_q = filter_q | Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
                queryset = queryset.filter(filter_q)

                # filter for read permissions for user
                queryset = filter_tagged_object_queryset_for_user(queryset, user)

            if sort_key:
                queryset = queryset.order_by(sort_key)
            else:
                queryset = queryset.order_by('-created')
        return queryset


class BasePagedOffsetWidgetView(BaseUserDashboardWidgetView):
    """Shows BaseTaggable content for the user"""

    model = None  # can be None, needs to be set in implementing widget view!
    # the model field on which to cut off the timed offset from, needs to be set in implementing widget view!
    offset_model_field = None

    default_page_size = 3
    min_page_size = 1
    max_page_size = 20

    # if given, will only return items *older* than the given timestamp!
    offset_timestamp = None
    default_offset_timestamp = None

    def get(self, request, *args, **kwargs):
        self.page_size = int(request.GET.get('page_size', self.default_page_size))
        if not is_number(self.page_size):
            return HttpResponseBadRequest('Malformed parameter: "page_size": %s' % self.page_size)
        self.page_size = max(self.min_page_size, min(self.max_page_size, self.page_size))

        self.offset_timestamp = request.GET.get('offset_timestamp', self.default_offset_timestamp)
        if self.offset_timestamp is not None and not is_number(self.offset_timestamp):
            return HttpResponseBadRequest('Malformed parameter: "offset_timestamp"')
        if self.offset_timestamp is not None and isinstance(self.offset_timestamp, six.string_types):
            self.offset_timestamp = float(self.offset_timestamp)

        self.set_options()
        return super(BasePagedOffsetWidgetView, self).get(request, *args, **kwargs)

    def set_options(self):
        """Optional additional function to set some options for overriding views"""
        pass

    def get_queryset(self):
        """Returns a queryset of sorted data"""
        return ImproperlyConfigured('Implement this function in your extending widget view!')

    def get_items_from_queryset(self, queryset):
        """Returns a list of converted item data from the queryset"""
        return ImproperlyConfigured('Implement this function in your extending widget view!')

    def get_data(self, **kwargs):
        queryset = self.get_queryset()

        # cut off at timestamp if given
        if self.offset_timestamp:
            offset_datetime = datetime_from_timestamp(self.offset_timestamp)
            filter_exp = {'%s__lt' % self.offset_model_field: offset_datetime}
            queryset = queryset.filter(**filter_exp)

        # calculate has_more and new offset timestamp
        has_more = queryset.count() > self.page_size
        queryset = queryset[: self.page_size]

        items = self.get_items_from_queryset(queryset)
        queryset = list(queryset)

        last_offset_timestamp = None
        if len(queryset) > 0:
            last_offset_timestamp = timestamp_from_datetime(getattr(queryset[-1], self.offset_model_field))

        return {
            'items': items,
            'widget_title': self.model._meta.verbose_name_plural if self.model else None,
            'has_more': has_more,
            'offset_timestamp': last_offset_timestamp,
        }


class TypedContentWidgetView(ModelRetrievalMixin, BasePagedOffsetWidgetView):
    """Shows BaseTaggable content for the user"""

    model = None
    # if True: will show only content that the user has recently visited
    # if False: will show all of the users content, sorted by creation date
    show_recent = False

    def get(self, request, *args, **kwargs):
        self.show_recent = kwargs.pop('show_recent', False)
        if self.show_recent:
            self.offset_model_field = 'visited'
        else:
            self.offset_model_field = 'created'

        content = kwargs.pop('content', None)
        if not content:
            return HttpResponseBadRequest('No content type supplied')
        self.model = SEARCH_MODEL_NAMES_REVERSE.get(content, None)
        if not self.model:
            return HttpResponseBadRequest('Unknown content type supplied: "%s"' % content)

        return super(TypedContentWidgetView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        if self.show_recent:
            # showing "last-visited" content, ordering by visit datetime
            ct = ContentType.objects.get_for_model(self.model)
            queryset = LastVisitedObject.objects.filter(
                content_type=ct, user=self.request.user, portal=CosinnusPortal.get_current()
            )

            # filter data in the way it shows only those entries which are related to the current user via his/her
            # `CosinnusGroupMembership`
            if issubclass(
                self.model, BaseTaggableObjectModel
            ):  # consider only those objects which have `group` FK-relation (i.e. not `messages`)
                user_group_ids = CosinnusGroupMembership.objects.filter(
                    Q(group__is_active=True) & Q(status__in=MEMBER_STATUS) & Q(user=self.request.user)
                ).values_list('group', flat=True)
                last_visited_objects_ids = self.model.objects.filter(group_id__in=user_group_ids).values_list(
                    'id', flat=True
                )
                queryset = queryset.filter(object_id__in=last_visited_objects_ids).order_by(
                    '-visited'
                )  # filtration via `id` shows only events; `object_id` covers all entries
        else:
            # all content, ordered by creation date
            only_mine = True
            sort_key = '-created'
            queryset = self.fetch_queryset_for_user(
                self.model, self.request.user, sort_key=sort_key, only_mine=only_mine
            )
            if queryset is None:
                return {'items': [], 'widget_title': '(error: %s)' % self.model.__name__}
        return queryset

    def get_items_from_queryset(self, queryset):
        """Returns a list of converted item data from the queryset"""
        if self.show_recent:
            # the `item_data` field already contains the JSON of `DashboardItem`
            items = list(queryset.values_list('item_data', flat=True))
        else:
            items = [DashboardItem(item, user=self.request.user) for item in list(queryset)]
        return items


api_user_typed_content = TypedContentWidgetView.as_view()


class TimelineView(ModelRetrievalMixin, View):
    """Timeline view for a user.
    Returns items as rendered HTML.
    Accepts content type filters and pagination parameters."""

    http_method_names = [
        'get',
    ]

    # which models can be displayed, as found in `SEARCH_MODEL_NAMES_REVERSE`
    content_types = [
        'polls',
        'todos',
        'files',
        'pads',
        'events',
        'notes',
    ]

    if settings.COSINNUS_IDEAS_ENABLED:
        content_types += ['ideas']

    if settings.COSINNUS_V2_DASHBOARD_SHOW_MARKETPLACE:
        content_types += ['offers']

    # the key by which the timeline stream is ordered. must be present on *all* models
    sort_key = '-last_action'

    page_size = None
    default_page_size = 10
    min_page_size = 1
    max_page_size = 200

    # if given, will only return items *older* than the given timestamp!
    offset_timestamp = None
    default_offset_timestamp = None

    only_mine = None
    only_mine_default = True

    only_forum = None
    only_forum_default = True

    only_public = None
    only_public_default = True

    filter_model = None  # if set, only show items of this model
    user = None  # set at initialization

    def get(self, request, *args, **kwargs):
        """Accepted GET-params:
        `page_size` int (optional): Number of items to be returned. If a value larger than
            `self.max_page_size` is supplied, `self.max_page_size`is used instead.
            Default: `self.default_page_size`
        `offset_timestamp` float (optional): If supplied, only items older than the given
            timestamp are returned. Items with the exact timestamp are excluded.
            Use this parameter in conjunction with the return value `last_timestamp` for
            pagination.
        `only_mine` bool (optional): if True, will include objects that belong to groups
            or projects the `user` is a member of.
        `only_forum` bool (optional): if True, will include objects that belong to the
            forum group.
        `only_public` bool (optional): if True, will include objects that are set to public
            specifically.

        """
        # require authenticated user
        self.user = request.user
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated.')
        content = kwargs.pop('content', None)
        if content:
            self.filter_model = SEARCH_MODEL_NAMES_REVERSE.get(content, None)
            if not self.filter_model:
                return HttpResponseBadRequest('Unknown content type supplied: "%s"' % content)

        self.page_size = int(request.GET.get('page_size', self.default_page_size))
        if not is_number(self.page_size):
            return HttpResponseBadRequest('Malformed parameter: "page_size": %s' % self.page_size)
        self.page_size = max(self.min_page_size, min(self.max_page_size, self.page_size))

        self.offset_timestamp = request.GET.get('offset_timestamp', self.default_offset_timestamp)
        if self.offset_timestamp is not None and not is_number(self.offset_timestamp):
            return HttpResponseBadRequest('Malformed parameter: "offset_timestamp"')
        if self.offset_timestamp is not None and isinstance(self.offset_timestamp, six.string_types):
            self.offset_timestamp = float(self.offset_timestamp)

        self.only_mine = request.GET.get('only_mine', self.only_mine_default)
        if isinstance(self.only_mine, six.string_types):
            self.only_mine = bool(json.loads(self.only_mine))
        self.only_forum = request.GET.get('only_forum', self.only_forum_default)
        if isinstance(self.only_forum, six.string_types):
            self.only_forum = bool(json.loads(self.only_forum))
        self.only_public = request.GET.get('only_public', self.only_public_default)
        if isinstance(self.only_public, six.string_types):
            self.only_public = bool(json.loads(self.only_public))

        items = self.get_items()
        response = self.render_to_response(items)
        return response

    def render_to_response(self, items):
        """Renders a list of items and returns a JsonResponse with the items
        and additional meta info.
        Returned data:
        @return:
            `items`: list[str]: a list of rendered html items
            `count` int: count of the number of rendered items
            `has_more` bool: if more items are potentially available
            `last_timestamp` float: the timestamp of the oldest returned item.
                used as offset for the next paginated request. Will be None
                if 0 items were returned.
        """
        rendered_items = [self.render_item(item) for item in items]
        last_timestamp = None
        if len(items) > 0:
            last_timestamp = timestamp_from_datetime(getattr(items[-1], self.sort_key_natural))
        response = {
            'items': rendered_items,
            'count': len(rendered_items),
            'has_more': len(rendered_items) == self.page_size,
            'last_timestamp': last_timestamp,
        }
        return JsonResponse({'data': response})

    def get_items(self):
        """Returns a paginated list of items as mixture of different models, in sorted order"""
        if self.filter_model:
            single_querysets = [self._get_queryset_for_model(self.filter_model)]
        else:
            single_querysets = []
            for content_type in self.content_types:
                content_model = SEARCH_MODEL_NAMES_REVERSE.get(content_type, None)
                if content_model is None:
                    if settings.DEBUG:
                        logger.warn('Could not find content model for timeline content type "%s"' % content_type)
                    continue
                qs = self._get_queryset_for_model(content_model)
                single_querysets.append(qs)

        # filter empty return values and mix the querysets
        single_querysets = [qs for qs in single_querysets if qs is not None]
        items = self._mix_items_from_querysets(*single_querysets)
        return items

    def render_item(self, item):
        """Renders an item using the template defined in its model's `timeline_template` attribute"""
        template = getattr(item, 'timeline_template', None)
        if template:
            context = {'item': item}
            html = render_to_string(template, context, self.request)
        else:
            if settings.DEBUG:
                raise ImproperlyConfigured(
                    'No `timeline_template` attribute found for item model "%s"' % item._meta.model
                )
            html = '<!-- Error: Timeline content for model "%s" could not be rendered.' % item._meta.model
        return html

    def _get_qs_for_forum(self, model):
        """Returns a qs for a model for only items from the forum groups/ideas"""
        return self.fetch_queryset_for_user(
            model,
            self.user,
            sort_key=self.sort_key,
            only_mine=False,
            only_mine_strict=False,
            only_forum=True,
        )

    def _get_qs_for_mine(self, model):
        """Returns a qs for a model for only items from the user's groups and NO forum groups/ideas"""
        # the only_mine mode here is a only_mine_strict!
        return self.fetch_queryset_for_user(
            model, self.user, sort_key=self.sort_key, only_mine=True, only_mine_strict=True
        )

    def _get_qs_for_public(self, model):
        """Returns a qs for a model for only specifically public items"""
        return self.fetch_queryset_for_user(
            model, self.user, sort_key=self.sort_key, only_mine=False, only_mine_strict=False, all_public=True
        )

    def _get_qs_for_everything(self, model):
        """Returns a qs for a model for everything the user could possibly see"""
        return self.fetch_queryset_for_user(
            model, self.user, sort_key=self.sort_key, only_mine=False, only_mine_strict=False
        )

    def _get_queryset_for_model(self, model):
        """Returns a *sorted* queryset of items of a model for a user depending
        on the filter switch settings"""
        # combine QS from the filter function depending on what flags are set
        flag_func_map = {
            'only_forum': self._get_qs_for_forum,
            'only_mine': self._get_qs_for_mine,
            'only_public': self._get_qs_for_public,
        }
        # if no flags are set, return None
        if all([not getattr(self, attr_name) for attr_name in flag_func_map.keys()]):
            return None
        # if all flags are set, we use the get-all function
        if all([getattr(self, attr_name) for attr_name in flag_func_map.keys()]):
            return self._get_qs_for_everything(model)

        # get each singular qs for each flag set, and if there is more than one, combine them
        querysets = []
        for attr_name, qs_func in flag_func_map.items():
            if getattr(self, attr_name):
                querysets.append(qs_func(model))

        combined_qs = querysets[0]
        extra_querysets = querysets[1:]
        if extra_querysets:
            for extra_qs in querysets:
                combined_qs = combined_qs | extra_qs
            combined_qs = combined_qs.distinct()

        # support for filtering out blocked users' content
        combined_qs = filter_base_taggable_qs_for_blocked_user_content(combined_qs, self.request.user)
        return combined_qs

    def _mix_items_from_querysets(self, *streams):
        """Will zip items from multiple querysts (each for a single model)
        into a single item list, while retainining an overall sort-order.
        Will peek all of the querysets and pick the next lowest-sorted item
        (honoring the given offset), until enough items for the page size are collected,
        or all querysets are exhausted."""
        if not streams:
            return []
        reverse = '-' in self.sort_key
        # apply timestamp offset
        if self.offset_timestamp:
            offset_datetime = datetime_from_timestamp(self.offset_timestamp)
            streams = [stream.filter(**{'%s__lt' % self.sort_key_natural: offset_datetime}) for stream in streams]

        if not getattr(settings, 'COSINNUS_V2_DASHBOARD_USE_NAIVE_FETCHING', False):
            queryset_iterator = QuerysetLazyCombiner(
                streams, self.sort_key_natural, math.ceil(self.page_size / 2.0), reverse=reverse
            )
            items = list(itertools.islice(queryset_iterator, self.page_size))
        else:
            logger.warn('Using naive queryset picking! Performance may suffer in production!')
            # naive just takes `page_size` items from each stream, then sorts and takes first `page_size` items
            cut_streams = [stream[: self.page_size] for stream in streams]
            items = sorted(
                itertools.chain(*cut_streams), key=lambda item: getattr(item, self.sort_key_natural), reverse=reverse
            )  # placeholder
            items = items[: self.page_size]

        return items

    @property
    def sort_key_natural(self):
        """Returns the sort_key without '-'"""
        return self.sort_key.replace('-', '')


api_timeline = TimelineView.as_view()
