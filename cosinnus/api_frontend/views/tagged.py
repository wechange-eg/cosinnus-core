from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.tagged import CosinnusGeocodeLocationSerializer
from cosinnus.utils.tagged import geocode_location


class GeocodeUserThrottle(UserRateThrottle):
    scope = 'tagged_geocode_view'
    rate = '100/hour'


class CosinnusGeocodeView(APIView):
    """
    Geocoding API.
    Returns a list of geolocation based on the "query" request parameter.
    If no query is set or the query length is below 3 en empty list is returned.
    If the user reaches the 100 requests / hour limit "HTTP 429 Too Many Requests" is returned.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    permission_classes = (IsAuthenticated,)
    throttle_classes = [GeocodeUserThrottle]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'query',
                openapi.IN_QUERY,
                description='Location String to query.',
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={200: CosinnusGeocodeLocationSerializer(many=True)},
    )
    def get(self, request):
        data = []
        query = request.query_params.get('query')
        if query and len(query) > 2:
            locations = geocode_location(query, request=request, exactly_one=False)
            serializer = CosinnusGeocodeLocationSerializer(locations, many=True)
            data = serializer.data
        return Response(data=data)
