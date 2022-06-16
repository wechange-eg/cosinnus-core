from django.utils import timezone
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.template import Context
from django.template.loader import render_to_string
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
from cosinnus.utils.permissions import IsCosinnusAdminUser
from cosinnus.utils.user import filter_active_users, get_user_id_hash, get_user_tos_accepted_date
from cosinnus.views.housekeeping import _get_group_storage_space_mb

from operator import itemgetter


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
    """
    renderer_classes = (SimpleStatisticsGroupConferenceStorageReportRenderer,) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (IsCosinnusAdminUser,)

    def get_group_storage_report(self, group_model=None):
        rows = []
        klass = group_model or CosinnusSociety
        for group in klass.objects.all_in_portal():
            projects = group.get_children()
            group_size = _get_group_storage_space_mb(group)
            projects_size = 0
            for project in projects:
                projects_size += _get_group_storage_space_mb(project)
            rows.append([group.get_absolute_url(), group.member_count, len(projects), group_size, group_size + projects_size])
        rows = sorted(rows, key=itemgetter(4), reverse=True)

        return rows

    def get(self, request, *args, **kwargs):

        group_storage_report = self.get_group_storage_report(group_model=None or CosinnusSociety)

        data = [
            {
            'urls': elem[0],
            'member_count': elem[1],
            'number_projects': elem[2],
            'group_storage_mb': elem[3],
            'group_and_projects_sum_mb': elem[4],
            } 
        for elem in group_storage_report]

        return Response(data)

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Appends Content-Disposition header to CSV requests and handles the file name.
        """
        if request.GET.get('format') == 'csv':
            response['Content-Disposition'] = 'attachment; filename=group-storage-report.csv'
        return super().finalize_response(request, response, *args, **kwargs) 


class SimpleStatisticsConferenceStorageReportView(APIView):
    """
    API endpoint for conference storage report overview.
    """
    renderer_classes = (SimpleStatisticsGroupConferenceStorageReportRenderer, ) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (IsCosinnusAdminUser,)

    def get_conference_storage_report(self, group_model=None):
        rows = []
        klass = group_model or CosinnusConference
        for group in klass.objects.all_in_portal():
            projects = group.get_children()
            group_size = _get_group_storage_space_mb(group)
            projects_size = 0
            for project in projects:
                projects_size += _get_group_storage_space_mb(project)
            rows.append([group.get_absolute_url(), group.member_count, len(projects), group_size, group_size + projects_size])
        rows = sorted(rows, key=itemgetter(4), reverse=True)

        return rows

    def get(self, request, *args, **kwargs):

        conference_storage_report = self.get_conference_storage_report(group_model=None or CosinnusConference)

        data = [
            {
            'urls': elem[0],
            'member_count': elem[1],
            'number_projects': elem[2],
            'group_storage_mb': elem[3],
            'group_and_projects_sum_mb': elem[4],
            } 
        for elem in conference_storage_report]

        return Response(data)

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Appends Content-Disposition header to CSV requests and handles the file name.
        """
        if request.GET.get('format') == 'csv':
            response['Content-Disposition'] = 'attachment; filename=conference-storage-report.csv'
        return super().finalize_response(request, response, *args, **kwargs) 


class SimpleStatisticsProjectStorageReportRenderer(CSVRenderer):
    """
    Renders the csv output with custom headers for project storage report API endpoint
    """
    header = ['urls', 'member_count', 'project_storage_mb']


class SimpleStatisticsProjectStorageReportView(APIView):
    """
    API endpoint for conference project report overview.
    """
    renderer_classes = (SimpleStatisticsProjectStorageReportRenderer,) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (IsCosinnusAdminUser,)

    def get_project_storage_report(self):
        rows = []
        for project in CosinnusProject.objects.all_in_portal():
            project_size = _get_group_storage_space_mb(project)
            rows.append([project.get_absolute_url(), project.member_count, project_size])
        rows = sorted(rows, key=itemgetter(2), reverse=True)

        return rows

    def get(self, request, *args, **kwargs):

        project_storage_report = self.get_project_storage_report()

        data = [
            {
            'urls': elem[0],
            'member_count': elem[1],
            'project_storage_mb': elem[2],
            } 
        for elem in project_storage_report]

        return Response(data)

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Renders the csv output with custom headers for project storage report API endpoint
        """
        if request.GET.get('format') == 'csv':
            response['Content-Disposition'] = 'attachment; filename=project-storage-report.csv'
        return super().finalize_response(request, response, *args, **kwargs) 


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
    """
    renderer_classes = (SimpleStatisticsUserActivityInfoRenderer, ) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (IsCosinnusAdminUser,)

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

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Renders the csv output with custom headers for project storage report API endpoint
        """
        if request.GET.get('format') == 'csv':
            response['Content-Disposition'] = 'attachment; filename=user_activity_info.csv'
        return super().finalize_response(request, response, *args, **kwargs) 


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
    """
    renderer_classes = (SimpleStatisticsBBBRoomVisitsRenderer, ) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
    permission_classes = (IsCosinnusAdminUser,)

    def get_bbb_room_visit_statistics(self):
        rows = []
        # cache for group_id (int) -> user
        group_admin_cache = {}
        # cache for user-hash user.id (int) --> hash (str)
        user_hash_cache = {}
        for visit in BBBRoomVisitStatistics.objects.all().order_by('visit_datetime').\
                prefetch_related('user', 'user__cosinnus_profile', 'user__cosinnus_profile__media_tag',
                                'group', 'bbb_room'):
            visitor = visit.user or None
            visitor_mt = visitor and visitor.cosinnus_profile and visitor.cosinnus_profile.media_tag or None
            # cache the group-admins
            visited_group_admin = group_admin_cache.get(visit.group_id, None)
            if visited_group_admin is None:
                visited_group_admins = visit.group and visit.group.actual_admins or []
                # only reporting data on the first admin for simplicity
                visited_group_admin = len(visited_group_admins) > 0 and visited_group_admins[0] or None
                group_admin_cache[visit.group_id] = visited_group_admin
            
            user_hash = user_hash_cache.get(visitor.id) if visitor else '<no-user>'
            if not user_hash:
                user_hash = get_user_id_hash(visitor)
                user_hash_cache[visitor.id] = user_hash
            
            rows.append([
                timezone.localtime(visit.visit_datetime).strftime('%Y-%m-%d %H:%M:%S'), # 'datetime',
                visit.group and visit.group.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_NAME, ''), #'conference_name',
                visit.group and visit.group.slug or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_SLUG, ''), #'conference_slug',
                ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_GROUP_MANAGED_TAG_SLUGS, [])]), #'conference_mtag_slugs',
                visited_group_admin.cosinnus_profile.language if visited_group_admin else '<no-user>', # conference_creator_email_language
                visit.bbb_room and visit.bbb_room.name or visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_ROOM_NAME, ''), #'room_name',
                user_hash, #'visitor_id',
                ','.join([str(item) for item in visit.data.get(BBBRoomVisitStatistics.DATA_DATA_SETTING_USER_MANAGED_TAG_SLUGS, [])]), #'visitor_mtag_slugs',
                visitor.cosinnus_profile.language if visitor else '<no-user>', # visitor_email_language
                visitor_mt and visitor_mt.location if visitor_mt else '', # visitor_location
                visitor_mt.location_lat if visitor_mt and visitor_mt.location else '', # visitor_location_lat
                visitor_mt.location_lon if visitor_mt and visitor_mt.location else '', # visitor_location_lon
            ])

        return rows

    def get(self, request, *args, **kwargs):

        bbb_room_visit_stats = self.get_bbb_room_visit_statistics()

        data = [
            {
                'datetime': elem[0],
                'conference_name': elem[1],
                'conference_slug': elem[2],
                'conference_mtag_slugs': elem[3],
                'conference_creator_email_language': elem[4],
                'room_name': elem[5],
                'visitor_hashed_id': elem[6],
                'visitor_mtag_slugs': elem[7],
                'visitor_email_language': elem[8],
                'visitor_location': elem[9],
                'visitor_location_lat': elem[10],
                'visitor_location_lon': elem[11],
            } 
        for elem in bbb_room_visit_stats]

        return Response(data)

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Renders the csv output with custom headers for project storage report API endpoint
        """
        if request.GET.get('format') == 'csv':
            response['Content-Disposition'] = 'attachment; filename=bbb-room-visits.csv'
        return super().finalize_response(request, response, *args, **kwargs) 


statistics = StatisticsView.as_view()
statistics_group_storage_info = SimpleStatisticsGroupStorageReportView.as_view()
statistics_conference_storage_info = SimpleStatisticsConferenceStorageReportView.as_view()
statistics_project_storage_info = SimpleStatisticsProjectStorageReportView.as_view()
statistics_user_activity_info = SimpleStatisticsUserActivityInfoView.as_view()
statictics_bbb_room_visits = SimpleStatisticsBBBRoomVisitsView.as_view()
header = HeaderView.as_view()
footer = FooterView.as_view()
settings = SettingsView.as_view()
