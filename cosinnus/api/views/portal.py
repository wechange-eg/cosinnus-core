from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.template import Context
from django.template.loader import render_to_string
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api.serializers.portal import PortalSettingsSerializer
from cosinnus.models import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.templatetags.cosinnus_tags import cosinnus_menu_v2,\
    cosinnus_footer_v2
from cosinnus.utils.user import filter_active_users


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


statistics = StatisticsView.as_view()
header = HeaderView.as_view()
footer = FooterView.as_view()
settings = SettingsView.as_view()
