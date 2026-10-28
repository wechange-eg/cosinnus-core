from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.personal_dashboard import (
    CosinnusPersonalDashboardAnnouncementSerializer,
    CosinnusPersonalDashboardWelcomeAnnouncementSerializer,
    CosinnusPersonalDashboardWidgetSerializer,
    CosinnusPersonalDashboardWidgetSettingsSerializer,
)
from cosinnus.models.personal_dashboard import WIDGET_TYPE_EXPLORE, WIDGET_TYPE_PERSONAL, get_personal_dashboard_widgets
from cosinnus.models.user_dashboard_announcement import UserDashboardAnnouncement, UserDashboardWelcomeAnnouncement
from cosinnus.utils.permissions import check_user_superuser


class CosinnusPersonalDashboardBaseWidgetsAPIView(ListAPIView):
    """Base API for v3 personal and explore dashboard widgets"""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    permission_classes = (IsAuthenticated,)
    serializer_class = CosinnusPersonalDashboardWidgetSerializer
    pagination_class = None


class CosinnusPersonalDashboardPersonalWidgetsAPIView(CosinnusPersonalDashboardBaseWidgetsAPIView):
    """An api for the v3 personal dashboard personal widgets."""

    def get_queryset(self):
        return get_personal_dashboard_widgets(widget_type=WIDGET_TYPE_PERSONAL)


class CosinnusPersonalDashboardExploreWidgetsAPIView(CosinnusPersonalDashboardBaseWidgetsAPIView):
    """An api for the v3 personal dashboard explore widgets."""

    def get_queryset(self):
        return get_personal_dashboard_widgets(widget_type=WIDGET_TYPE_EXPLORE)


class CosinnusPersonalDashboardWidgetSettingsAPIView(APIView):
    """An api for the v3 personal dashboard settings."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(request_body=CosinnusPersonalDashboardWidgetSettingsSerializer)
    def post(self, request):
        serializer = CosinnusPersonalDashboardWidgetSettingsSerializer(
            data=request.data, many=True, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()


class CosinnusPersonalDashboardAnnouncementAPIView(APIView):
    """An api for the v3 personal dashboard announcement."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Personal dashboard announcement', CosinnusPersonalDashboardAnnouncementSerializer)
        }
    )
    def get(self, request):
        preview_announcement_id = request.query_params.get('show_announcement')
        if preview_announcement_id and check_user_superuser(request.user):
            announcement = UserDashboardAnnouncement.objects.filter(pk=preview_announcement_id).first()
        else:
            announcement = UserDashboardAnnouncement.get_next_for_user(request.user)
        data = {}
        if announcement:
            serializer = CosinnusPersonalDashboardAnnouncementSerializer(announcement, context={'request': request})
            data = serializer.data
        return Response(data)

    @swagger_auto_schema(request_body=CosinnusPersonalDashboardAnnouncementSerializer)
    def post(self, request):
        serializer = CosinnusPersonalDashboardAnnouncementSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()


class CosinnusPersonalDashboardWelcomeAnnouncementAPIView(APIView):
    """An api for the v3 personal dashboard welcome announcement."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        responses={200: openapi.Response('Welcome annoucement', CosinnusPersonalDashboardWelcomeAnnouncementSerializer)}
    )
    def get(self, request):
        welcome_announcement = UserDashboardWelcomeAnnouncement.objects.first()
        if welcome_announcement:
            preview_welcome_announcement = request.query_params.get(
                'show_welcome_announcement'
            ) is not None and check_user_superuser(request.user)
            if not preview_welcome_announcement and not welcome_announcement.show_to_user(request.user):
                welcome_announcement = None
        data = None
        if welcome_announcement:
            serializer = CosinnusPersonalDashboardWelcomeAnnouncementSerializer(
                welcome_announcement, context={'request': request}
            )
            data = serializer.data
        return Response(data)

    @swagger_auto_schema(request_body=CosinnusPersonalDashboardWelcomeAnnouncementSerializer)
    def post(self, request):
        serializer = CosinnusPersonalDashboardWelcomeAnnouncementSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()
