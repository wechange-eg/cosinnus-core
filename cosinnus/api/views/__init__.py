import json

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db.models import Q
from django.http import HttpResponse
from django.template import Context
from django.template.loader import render_to_string
from oauth2_provider.decorators import protected_resource
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.user import filter_active_users
from ..serializers.group import CosinnusSocietySerializer, CosinnusProjectSerializer
from ..serializers.portal import PortalSettingsSerializer
from ..serializers.user import UserSerializer
from ...templatetags.cosinnus_tags import cosinnus_menu_v2


class PublicCosinnusGroupFilterMixin(object):

    def get_queryset(self):
        queryset = super().get_queryset()
        # filter for current portal
        queryset = queryset.filter(portal=CosinnusPortal.get_current())
        # Filter visibility
        queryset = queryset.filter(is_active=True)
        return queryset


class PublicTaggableObjectFilterMixin(object):

    def get_queryset(self):
        queryset = self.queryset
        # filter for current portal
        queryset = queryset.filter(group__portal=CosinnusPortal.get_current())
        # Filter visibility
        queryset = queryset.filter(group__is_active=True, media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        return queryset


class CosinnusFilterQuerySetMixin(object):
    FILTER_CONDITION_MAP = {
        'avatar': {
            'true': [~Q(avatar="")],
            'false': [Q(avatar="")],
        }
    }
    FILTER_KEY_MAP = {
        'tags': 'media_tag__tags__name',
    }
    FILTER_VALUE_MAP = {
        'false': False,
        'true': True
    }
    FILTER_DEFAULT_ORDER = ['-created', ]
    MANAGED_TAGS_KEY = 'managed_tags'
    # if true, filter managed tags on the group of the object, not on the object itself
    MANAGED_TAGS_FILTER_ON_GROUP = False

    def get_queryset(self):
        """
        Optionally filter by group
        FIXME: Use generic filters here after upgrade to django-filter==0.15.0
        """
        queryset = super().get_queryset()
        # Order
        query_params = self.request.query_params.copy()
        order_by = query_params.pop('order_by', self.FILTER_DEFAULT_ORDER)
        queryset = queryset.order_by(*order_by)
        # Managed tag filters
        if self.MANAGED_TAGS_KEY in query_params:
            managed_tags = query_params.getlist(self.MANAGED_TAGS_KEY)
            mtag_filter_prefix = 'group__' if self.MANAGED_TAGS_FILTER_ON_GROUP else ''
            mtag_filter = {
                f'{mtag_filter_prefix}managed_tag_assignments__managed_tag__slug__in': managed_tags,
                f'{mtag_filter_prefix}managed_tag_assignments__approved': True
            }
            queryset = queryset.filter(**mtag_filter)
            query_params.pop(self.MANAGED_TAGS_KEY)
        # Overwrite ugly but commonly used filters
        for key, value in list(query_params.items()):
            if key in (self.pagination_class.limit_query_param,
                       self.pagination_class.offset_query_param):
                continue
            if key in self.FILTER_CONDITION_MAP:
                VALUE_MAP = self.FILTER_CONDITION_MAP.get(key)
                if value in VALUE_MAP:
                    queryset = queryset.filter(*VALUE_MAP.get(value))
            else:
                key = self.FILTER_KEY_MAP.get(key, key)
                value = self.FILTER_VALUE_MAP.get(value, value)
                if value is None:
                    continue
                if key.startswith('exclude_'):
                    queryset = queryset.exclude(**{key[8:]: value})
                else:
                    queryset = queryset.filter(**{key: value})
        return queryset


class CosinnusPaginateMixin(object):
    
    def get_queryset(self):
        queryset = super().get_queryset()
        page = self.paginate_queryset(queryset)
        return page


class CosinnusSocietyViewSet(CosinnusFilterQuerySetMixin,
                             PublicCosinnusGroupFilterMixin,
                             viewsets.ReadOnlyModelViewSet):
    queryset = CosinnusSociety.objects.all()
    serializer_class = CosinnusSocietySerializer


class CosinnusProjectViewSet(CosinnusSocietyViewSet):

    queryset = CosinnusProject.objects.all()
    serializer_class = CosinnusProjectSerializer


class OAuthUserView(APIView):
    """
    Used by Oauth2 authentication (Rocket.Chat) to retrieve user details
    """

    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ""
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            return Response({
                'success': True,
                'id': user.username if user.username.isdigit() else str(user.id),
                'email': user.email.lower(),
                'name': user.get_full_name(),
                'avatar': avatar_url,
            })
        else:
            return Response({
                'success': False,
            })


@protected_resource(scopes=['read'])
def oauth_user(request):
    return HttpResponse(json.dumps(
        {
            'id': request.resource_owner.id,
            'username': request.resource_owner.username,
            'email': request.resource_owner.email,
            'first_name': request.resource_owner.first_name,
            'last_name': request.resource_owner.last_name
        }
    ), content_type="application/json")


@protected_resource(scopes=['read'])
def oauth_profile(request):
    profile = request.resource_owner.cosinnus_profile
    media_tag_fields = ['visibility', 'location',
                        'location_lat', 'location_lon',
                        'place', 'valid_start', 'valid_end',
                        'approach']

    media_tag = profile.media_tag
    media_tag_dict = {}
    if media_tag:
        for field in media_tag_fields:
            media_tag_dict[field] = getattr(media_tag, field)

    return HttpResponse(json.dumps(
        {
            'avatar': profile.avatar_url,
            'description': profile.description,
            'website': profile.website,
            'language': profile.language,
            'media_tag': media_tag_dict
        }
    ), content_type="application/json")


@api_view(['GET'])
def current_user(request):
    """
    Determine the current user by their JWT token, and return their data
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


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


class NavBarView(APIView):
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
                static('js/cosinnus.js') + '?v=0.47',
                static('js/vendor/underscore-1.8.3.js'),
                static('js/vendor/backbone-1.3.3.js'),
                static('js/client.js'),
            ]
        })


class SettingsView(APIView):
    """
    Returns portal settings
    """

    def get(self, request):
        serializer = PortalSettingsSerializer(CosinnusPortal.get_current())
        return Response(serializer.data)


oauth_current_user = OAuthUserView.as_view()
statistics = StatisticsView.as_view()
navbar = NavBarView.as_view()
settings = SettingsView.as_view()
