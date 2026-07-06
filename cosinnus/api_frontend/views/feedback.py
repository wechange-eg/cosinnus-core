from django.apps import apps
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.feedback import CosinnusReportSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication


class CosinnusReportView(APIView):
    """API for complaint reports.
    The report target model is set via the model_name init parameter in the views url definition.
    E.g.: CosinnusReportView.as_view(model_name='cosinnus_event.Event')
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    # report target model set via view parameter
    model_name = None

    @swagger_auto_schema(request_body=CosinnusReportSerializer)
    def post(self, request):
        # get model class
        app_label, model = self.model_name.split('.')
        model_cls = apps.get_model(app_label, model)

        # serialize data
        serializer = CosinnusReportSerializer(model_cls=model_cls, data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            # create report
            serializer.save()
        return Response()
