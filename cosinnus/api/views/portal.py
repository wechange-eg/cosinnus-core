from django.utils import timezone
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.template import Context
from django.template.loader import render_to_string
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer
from django.utils.timezone import now

from cosinnus.api.serializers.portal import PortalSettingsSerializer
from cosinnus.conf import settings as cosinnus_settings
from cosinnus.models import CosinnusPortal, MEMBERSHIP_ADMIN
from cosinnus.models.bbb_room import BBBRoomVisitStatistics
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject, CosinnusConference
from cosinnus.templatetags.cosinnus_tags import cosinnus_menu_v2,\
    cosinnus_footer_v2
from cosinnus.utils.user import filter_active_users, get_user_id_hash, get_user_tos_accepted_date
from cosinnus.views.housekeeping import _get_group_storage_space_mb

from itertools import zip_longest


class StatisticsView(APIView):
    """
    Returns a JSON dict of common statistics for this portal
    """

    def get_user_qs(self):
        return get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members)

    def get_society_qs(self):
        return CosinnusSociety.objects.all_in_portal()

    def get_project_qs(self):
        return CosinnusProject.objects.all_in_portal()

    def get_event_qs(self):
        from cosinnus_event.models import Event
        return Event.get_current_for_portal()

    def get_note_qs(self):
        from cosinnus_note.models import Note
        return Note.get_current_for_portal()

    def get(self, request, *args, **kwargs):
        all_users_qs = self.get_user_qs()
        data = {
            'groups': self.get_society_qs().count(),
            'projects': self.get_project_qs().count(),
            'users_registered': all_users_qs.count(),
            'users_active': filter_active_users(all_users_qs).count(),
        }
        try:
            data.update({
                'events_upcoming': self.get_event_qs().count(),
            })
        except:
            pass

        try:
            data.update({
                'notes': self.get_note_qs().count(),
            })
        except:
            pass

        return Response(data)


class StatisticsManagedTagFilteredView(StatisticsView):
    """
    Returns a JSON dict of common statistics for this portal, filtered for a managed tag
    """

    tag_slug = None

    def get(self, request, *args, **kwargs):
        self.tag_slug = kwargs.pop('slug', None)
        return super(StatisticsManagedTagFilteredView, self).get(request, *args, **kwargs)

    def get_user_qs(self):
        qs = super(StatisticsManagedTagFilteredView, self).get_user_qs()
        if self.tag_slug:
            qs = qs.filter(cosinnus_profile__managed_tag_assignments__managed_tag__slug=self.tag_slug)
        return qs

    def get_society_qs(self):
        qs = super(StatisticsManagedTagFilteredView, self).get_society_qs()
        if self.tag_slug:
            qs = qs.filter(managed_tag_assignments__managed_tag__slug=self.tag_slug)
        return qs

    def get_project_qs(self):
        qs = super(StatisticsManagedTagFilteredView, self).get_project_qs()
        if self.tag_slug:
            qs = qs.filter(managed_tag_assignments__managed_tag__slug=self.tag_slug)
        return qs

    def get_event_qs(self):
        qs = super(StatisticsManagedTagFilteredView, self).get_event_qs()
        if self.tag_slug:
            qs = qs.filter(group__managed_tag_assignments__managed_tag__slug=self.tag_slug)
        return qs

    def get_note_qs(self):
        qs = super(StatisticsManagedTagFilteredView, self).get_note_qs()
        if self.tag_slug:
            qs = qs.filter(group__managed_tag_assignments__managed_tag__slug=self.tag_slug)
        return qs


class HeaderView(APIView):
    """
    Returns navigation including styles to be included within Wordpress
    """

    def get(self, request):
        context = Context({'request': request})
        return Response({
            'html': cosinnus_menu_v2(context, request=request),
            'css': [
                static('css/all.min.css'),
                static('css/bootstrap3-cosinnus.css'),
                static('css/vendor/font-awesome-5/css/all.css'),
                static('css/vendor/select2.css'),
                static('css/cosinnus.css'),
            ],
            'js_settings': render_to_string('cosinnus/v2/navbar/js_settings.html', context.flatten(), request=request),
            'js': [
                static('js/vendor/jquery-2.1.0.min.js'),
                static('js/vendor/bootstrap.min.js'),
                static('js/vendor/moment-with-locales.min.js'),
                static('js/vendor/moment-timezone-with-data.min.js'),
                static('js/cosinnus.js') + '?v=0.47',
                static('js/vendor/underscore-1.8.3.js'),
                static('js/vendor/backbone-1.3.3.js'),
                static('js/client.js'),
            ]
        })


class FooterView(APIView):
    """
    Returns navigation including styles to be included within Wordpress
    """
    def get(self, request):
        context = Context({'request': request})
        return Response({
            'html': cosinnus_footer_v2(context, request=request),
        })


class SettingsView(APIView):
    """
    Returns portal settings
    """

    def get(self, request):
        serializer = PortalSettingsSerializer(CosinnusPortal.get_current())
        return Response(serializer.data)


class SimpleStatisticsGroupConferenceStorageReportRenderer(CSVRenderer):
    """
    Renders the csv output with custom headers for group and conference storage report API endpoints
    """
    header = ['urls', 'member_count', 'number_projects', 'group_storage_mb', 'group_and_projects_sum_mb']


class SimpleStatisticsGroupStorageReportView(APIView):
    """
    API endpoint for group storage report overview.
    Basically a refactoring for `group_storage_report_csv` function.
    """
    renderer_classes = (SimpleStatisticsGroupConferenceStorageReportRenderer,) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (permissions.IsAdminUser,)

    def get_group_urls(self, groups):
        group_urls = [group.get_absolute_url() for group in groups]
        return group_urls
    
    def get_member_count(self, groups):
        group_members = [group.member_count for group in groups]
        return group_members

    def get_number_projects(self, groups):
        projects = [group.get_children() for group in groups]
        project_lens = [len(project) for project in projects]
        return project_lens

    def get_group_size(self, groups):
        groups_qs = [group for group in groups]
        group_sizes = [_get_group_storage_space_mb(group) for group in groups_qs]
        return group_sizes
  
    def get_group_and_project_sum_size(self, groups):
        projects = [group.get_children() for group in groups]
        projects_sizes = [_get_group_storage_space_mb(val) for sublist in projects for val in sublist]
        result = [x+y for x, y in zip_longest(projects_sizes, self.get_group_size(groups), fillvalue=0)]
        return result

    def get(self, request, *args, **kwargs):
        groups = CosinnusSociety.objects.all_in_portal()

        group_urls = self.get_group_urls(groups)
        member_count = self.get_member_count(groups)
        number_of_projects = self.get_number_projects(groups)
        group_storage_mb = self.get_group_size(groups)
        group_and_projects_sum_mb = self.get_group_and_project_sum_size(groups)

        data = [
            {
                'urls': group_urls[i], 
                'member_count': member_count[i], 
                'number_projects': number_of_projects[i],
                'group_storage_mb': group_storage_mb[i],
                'group_and_projects_sum_mb': group_and_projects_sum_mb[i],
            }
            for i in range(len(group_urls))
        ]

        return Response(data)


class SimpleStatisticsConferenceStorageReportView(APIView):
    """
    API endpoint for conference storage report overview.
    Basically a refactoring for `conference_storage_report_csv` function.
    """
    renderer_classes = (SimpleStatisticsGroupConferenceStorageReportRenderer, ) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (permissions.IsAdminUser,)

    def get_conference_urls(self, conferences):
        conference_urls = [conference.get_absolute_url() for conference in conferences]
        return conference_urls
    
    def get_member_count(self, conferences):
        conference_members = [conference.member_count for conference in conferences]
        return conference_members

    def get_number_projects(self, conferences):
        projects = [conference.get_children() for conference in conferences]
        project_lens = [len(project) for project in projects]
        return project_lens

    def get_conference_size(self, conferences):
        conferences = [conference for conference in conferences]
        conference_sizes = [_get_group_storage_space_mb(conference) for conference in conferences]
        return conference_sizes

    def get_group_and_project_sum_size(self, conferences):
        projects = [conference.get_children() for conference in conferences]
        projects_sizes = [_get_group_storage_space_mb(val) for sublist in projects for val in sublist]
        result = [x+y for x, y in zip_longest(projects_sizes, self.get_conference_size(conferences), fillvalue=0)]
        return result

    def get(self, request, *args, **kwargs):
        conferences = CosinnusConference.objects.all_in_portal()

        conference_urls = self.get_conference_urls(conferences)
        member_count = self.get_member_count(conferences)
        number_of_projects = self.get_number_projects(conferences)
        group_storage_mb = self.get_conference_size(conferences)
        group_and_projects_sum_mb = self.get_group_and_project_sum_size(conferences)

        data = [
            {
                'urls': conference_urls[i], 
                'member_count': member_count[i], 
                'number_projects': number_of_projects[i],
                'group_storage_mb': group_storage_mb[i],
                'group_and_projects_sum_mb': group_and_projects_sum_mb[i],
            }
            for i in range(len(conference_urls))
        ]

        return Response(data)


class SimpleStatisticsProjectStorageReportRenderer(CSVRenderer):
    """
    Renders the csv output with custom headers for project storage report API endpoint
    """
    header = ['urls', 'member_count', 'project_storage_mb']


class SimpleStatisticsProjectStorageReportView(APIView):
    """
    API endpoint for project storage report overview.
    Basically a refactoring for `project_storage_report_csv` function.
    """
    renderer_classes = (SimpleStatisticsProjectStorageReportRenderer,) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (permissions.IsAdminUser,)

    def get_project_urls(self, projects_in_portal):
        project_urls = [project.get_absolute_url() for project in projects_in_portal]
        return project_urls

    def get_member_count(self, projects_in_portal):
        group_members = [group.member_count for group in projects_in_portal]
        return group_members
    
    def get_project_size(self, projects_in_portal):
        projects = [project for project in projects_in_portal]
        project_sizes = [_get_group_storage_space_mb(project) for project in projects]
        return project_sizes

    def get(self, request, *args, **kwargs):
        projects_in_portal = CosinnusProject.objects.all_in_portal()

        project_urls = self.get_project_urls(projects_in_portal)
        member_count = self.get_member_count(projects_in_portal)
        project_storage_mb = self.get_project_size(projects_in_portal)

        data = [
            {
                'urls': project_urls[i], 
                'member_count': member_count[i],
                'project_storage_mb': project_storage_mb[i],
            }
            for i in range(len(projects_in_portal))
        ]

        return Response(data)


class SimpleStatisticsUserActivityInfoRenderer(CSVRenderer):
    """
    Renders the csv output with custom headers for user activity information API endpoint
    """
    header = [
        'user-hashed-id', 
        'conferences-count',
        'admin-of-conferences-count',
        'projects-and-groups-count',
        'groups-only-count',
        'projects-only-count',
        'admin-of-projects-and-groups-count',
        'user-last-authentication-login-days',
        'current-tos-accepted',
        'registration-date',
        'events-attended',
    ]


class SimpleStatisticsUserActivityInfoView(APIView):
    """
    API endpoint for user activity information overview.
    Basically a refactoring for `user_activity_info` function.
    """
    renderer_classes = (SimpleStatisticsUserActivityInfoRenderer, ) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (permissions.IsAdminUser,)

    def get_user_activity_stats(self):
        users = {}
        portal = CosinnusPortal.get_current()
        headers = [
            'user-hashed-id',
        ]
        offset = 1
        if cosinnus_settings.COSINNUS_CONFERENCES_ENABLED:
            headers += [
                'conferences-count',
                'admin-of-conferences-count',
            ]
            offset += 2
        headers += [
            'projects-and-groups-count',
            'groups-only-count',
            'projects-only-count',
            'admin-of-projects-and-groups-count',
            'user-last-authentication-login-days',
            'current-tos-accepted',
            'registration-date',
            'events-attended',
        ]
        group_type_cache = {} # id (int) --> group type (int)
        for membership in CosinnusGroupMembership.objects.filter(group__portal=CosinnusPortal.get_current(), user__is_active=True).exclude(user__last_login__exact=None):
            # get the statistics row for the user of the membership, if there already is one we're aggregating
            user_row = users.get(membership.user_id, None)
            if user_row is None:
                user = membership.user
                if not hasattr(user, 'cosinnus_profile'):
                    continue
                initial_row = [
                    get_user_id_hash(user),         # 'user-hashed-id'
                ]
                if cosinnus_settings.COSINNUS_CONFERENCES_ENABLED:
                    initial_row += [
                        0,                          # 'conferences-count',
                        0,                          # 'admin-of-conferences-count',
                    ]
                tos_accepted_date = get_user_tos_accepted_date(user)
                tos_accepted = 1
                if portal.tos_date.year > 2000 and (tos_accepted_date is None or tos_accepted_date < portal.tos_date):
                    tos_accepted = 0
                initial_row += [
                    0,                              # 'projects-and-groups-count',
                    0,                              # 'groups-only-count',
                    0,                              # 'projects-only-count',
                    0,                              # 'admin-of-projects-and-groups-count',
                    (now()-user.last_login).days,   # 'user-last-login-days',
                    tos_accepted,                   # 'current-tos-accepted',
                    user.date_joined,               # 'registration-date',
                    0,                              # 'events-attended',
                ]
                user_row = initial_row
            
            group_type = group_type_cache.get(membership.group_id, None)
            if group_type is None:
                group_type = membership.group.type
                group_type_cache[membership.group_id] = group_type
                
            if cosinnus_settings.COSINNUS_CONFERENCES_ENABLED:
                if group_type == CosinnusGroup.TYPE_CONFERENCE:
                    user_row[1] += 1 # 'conferences-count'
                    if membership.status == MEMBERSHIP_ADMIN:
                        user_row[2] += 1 # 'admin-of-conferences-count',
            user_row[offset] += 1 # 'projects-and-groups-count'
            if group_type == CosinnusGroup.TYPE_PROJECT:
                user_row[offset+1] += 1 # 'groups-only-count'
            if group_type == CosinnusGroup.TYPE_SOCIETY:
                user_row[offset+2] += 1 # 'projects-only-count'
            if group_type in [CosinnusGroup.TYPE_SOCIETY, CosinnusGroup.TYPE_PROJECT] and membership.status == MEMBERSHIP_ADMIN:
                user_row[offset+3] += 1 # 'admin-of-projects-and-groups-count'
            
            users[membership.user_id] = user_row
        
        # add event attendance stats
        from cosinnus_event.models import EventAttendance # noqa
        for attendance in EventAttendance.objects.filter(state=EventAttendance.ATTENDANCE_GOING):
            user_row = users.get(attendance.user_id, None)
            if user_row is None:
                continue
            user_row[offset+7] += 1
        
        rows = users.values()
        rows = sorted(rows, key=lambda row: row[offset], reverse=True)

        return rows

    def get(self, request, *args, **kwargs):

        user_activity_stats = self.get_user_activity_stats()

        data = [
            {
            'user-hashed-id': elem[0],
            'conferences-count': elem[1],
            'admin-of-conferences-count': elem[2],
            'projects-and-groups-count': elem[3],
            'groups-only-count': elem[4],
            'projects-only-count': elem[5],
            'admin-of-projects-and-groups-count': elem[6],
            'user-last-authentication-login-days': elem[7],
            'current-tos-accepted': elem[8],
            'registration-date': timezone.localtime(elem[9]).strftime('%Y-%m-%d %H:%M:%S'),
            'events-attended': elem[10],
            } 
        for elem in user_activity_stats]

        return Response(data)


class SimpleStatisticsBBBRoomVisitsRenderer(CSVRenderer):
    """
    Renders the csv output with custom headers for BBB room visit statistics API endpoint
    """
    header = [
        'datetime',
        'conference_name',
        'conference_slug',
        'conference_mtag_slugs',
        'conference_creator_email_language',
        'room_name',
        'visitor_hashed_id',
        'visitor_mtag_slugs',
        'visitor_email_language',
        'visitor_location',
        'visitor_location_lat',
        'visitor_location_lon',
    ]


class SimpleStatisticsBBBRoomVisitsView(APIView):
    """
    API endpoint for BBB room visit statistics overview.
    Basically a refactoring for `bbb_room_visit_statistics_download` function.
    """
    renderer_classes = (SimpleStatisticsBBBRoomVisitsRenderer, ) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (permissions.IsAdminUser,)

    def get_datetime(self, bbb_room_visits):
        visit_time = [timezone.localtime(visit.visit_datetime).strftime('%Y-%m-%d %H:%M:%S') for visit in bbb_room_visits]
        return visit_time

    def get_conference_name(self, bbb_room_visits):
        visit_conference_names = [visit.group and visit.group.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_NAME, '') for visit in bbb_room_visits]
        return visit_conference_names

    def get_conference_slug(self, bbb_room_visits):
        visit_conference_slugs = [visit.group and visit.group.slug or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_SLUG, '') for visit in bbb_room_visits]
        return visit_conference_slugs

    def get_conference_mtag_slugs(self, bbb_room_visits):
        visit_managed_tags = [visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS, '') for visit in bbb_room_visits]
        result = [val for sublist in visit_managed_tags for val in sublist]
        return result

    def get_conference_creator_email_language(self, bbb_room_visits):
        visited_group_admins = [visit.group and visit.group.actual_admins or [] for visit in bbb_room_visits]
        result = [visitor[0].cosinnus_profile.language if visitor != [] else '<no-user>' for visitor in visited_group_admins]
        return result

    def get_room_name(self, bbb_room_visits):
        visit_room_names = [visit.bbb_room and visit.bbb_room.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_ROOM_NAME, '') for visit in bbb_room_visits]
        return visit_room_names

    def get_visitor_hashed_id(self, bbb_room_visits):
        visitor_hashes = [get_user_id_hash(visit.user) for visit in bbb_room_visits]
        return visitor_hashes

    def get_visitor_mtag_slugs(self, bbb_room_visits):
        visitor_managed_tags = [visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS, '') for visit in bbb_room_visits]
        result = [val for sublist in visitor_managed_tags for val in sublist]
        return result

    def get_visitor_email_language(self, bbb_room_visits):
        visitors = [visit.user for visit in bbb_room_visits]
        result = [visitor.cosinnus_profile.language for visitor in visitors]
        return result

    def get_visitor_location(self, bbb_room_visits):
        visitors = [visit.user and visit.user.cosinnus_profile and visit.user.cosinnus_profile.media_tag for visit in bbb_room_visits]
        result = [visitor.location for visitor in visitors]
        return result

    def get_visitor_location_lat(self, bbb_room_visits):
        visitors = [visit.user and visit.user.cosinnus_profile and visit.user.cosinnus_profile.media_tag for visit in bbb_room_visits]
        result = [str(visitor.location_lat) if visitor.location else '' for visitor in visitors]
        return result

    def get_visitor_location_lon(self, bbb_room_visits):
        visitors = [visit.user and visit.user.cosinnus_profile and visit.user.cosinnus_profile.media_tag for visit in bbb_room_visits]
        result = [str(visitor.location_lon) if visitor.location else '' for visitor in visitors]
        return result
    
    def get(self, request, *args, **kwargs):
        bbb_room_visits = BBBRoomVisitStatistics.objects.all().order_by('visit_datetime')

        datetime = self.get_datetime(bbb_room_visits)
        conference_name = self.get_conference_name(bbb_room_visits)
        conference_slug = self.get_conference_slug(bbb_room_visits),
        conference_mtag_slugs = self.get_conference_mtag_slugs(bbb_room_visits),
        conference_creator_email_language = self.get_conference_creator_email_language(bbb_room_visits),
        room_name = self.get_room_name(bbb_room_visits),
        visitor_hashed_id = self.get_visitor_hashed_id(bbb_room_visits),
        visitor_mtag_slugs = self.get_visitor_mtag_slugs(bbb_room_visits),
        visitor_email_language = self.get_visitor_email_language(bbb_room_visits),
        visitor_location = self.get_visitor_location(bbb_room_visits),
        visitor_location_lat = self.get_visitor_location_lat(bbb_room_visits),
        visitor_location_lon = self.get_visitor_location_lon(bbb_room_visits),

        data = [
            {
                'datetime': datetime[i],
                'conference_name': conference_name[i],
                'conference_slug': ','.join([str(elem[i]) for elem in conference_slug]), # nested loop from here onwards as workaround for avoiding `IndexError: tuple index out of range`
                'conference_mtag_slugs': ','.join([str(elem[i]) for elem in conference_mtag_slugs]),
                'conference_creator_email_language': ','.join([str(elem[i]) for elem in conference_creator_email_language]),
                'room_name': ','.join([str(elem[i]) for elem in room_name]),
                'visitor_hashed_id': ','.join([str(elem[i]) for elem in visitor_hashed_id]),
                'visitor_mtag_slugs': ','.join([str(elem[i]) for elem in visitor_mtag_slugs]),
                'visitor_email_language': ','.join([str(elem[i]) for elem in visitor_email_language]),
                'visitor_location': ','.join([str(elem[i]) for elem in visitor_location]),
                'visitor_location_lat': ','.join([str(elem[i]) for elem in visitor_location_lat]),
                'visitor_location_lon': ','.join([str(elem[i]) for elem in visitor_location_lon]),
            }
            for i in range(len(bbb_room_visits))
        ]

        return Response(data)


statistics = StatisticsView.as_view()
statistics_group_storage_info = SimpleStatisticsGroupStorageReportView.as_view()
statistics_conference_storage_info = SimpleStatisticsConferenceStorageReportView.as_view()
statistics_project_storage_info = SimpleStatisticsProjectStorageReportView.as_view()
statistics_user_activity_info = SimpleStatisticsUserActivityInfoView.as_view()
statictics_bbb_room_visits = SimpleStatisticsBBBRoomVisitsView.as_view()
header = HeaderView.as_view()
footer = FooterView.as_view()
settings = SettingsView.as_view()
