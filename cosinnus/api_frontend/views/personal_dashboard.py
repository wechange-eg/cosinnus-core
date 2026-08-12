from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.personal_dashboard import CosinnusPersonalDashboardSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication


class CosinnusPersonalDashboardAPIView(APIView):
    """An api for the v3 personal dashboard."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(responses={200: openapi.Response('User dashboard data', CosinnusPersonalDashboardSerializer)})
    def get(self, request):
        serializer = CosinnusPersonalDashboardSerializer(
            context={'user': request.user, 'query_params': request.query_params}
        )
        return Response(serializer.data)

    @swagger_auto_schema(request_body=CosinnusPersonalDashboardSerializer)
    def patch(self, request):
        serializer = CosinnusPersonalDashboardSerializer(
            data=request.data, partial=True, context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.get(request)
