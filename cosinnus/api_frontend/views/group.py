from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import NotFound
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.group import GroupSettingsSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import IsCosinnusGroupUser


class GroupSettingsView(APIView):
    """An endpoint that returns configured settings/properties for a group."""

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsCosinnusGroupUser,)

    group = None

    def initial(self, request, *args, **kwargs):
        # get group
        group_id = kwargs.get('group_id')
        self.group = get_cosinnus_group_model().objects.filter(is_active=True, pk=group_id).first()
        if not self.group:
            raise NotFound()
        return super().initial(request, *args, **kwargs)

    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='A list of objects containing the id for a topic as "value" and its label as "title".',
                examples={
                    'application/json': {
                        'data': {
                            'bbb_available': True,
                            'bbb_restricted': False,
                            'events_ical_url': 'https://localhost:8000/events/team/7/feed/',
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request, group_id):
        serializer = GroupSettingsSerializer(self.group)
        return Response(serializer.data)
