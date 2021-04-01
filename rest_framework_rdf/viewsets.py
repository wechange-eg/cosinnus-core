from rest_framework.settings import api_settings
from rest_framework_rdf.renderers import TurtleRenderer
from rest_framework_rdf.serializers import RDFSerializer


class TextTurtleRenderer(TurtleRenderer):
    media_type = 'text/turtle'


class RDFViewSetMixin:
    rdf_renderer_classes = [TextTurtleRenderer, ]
    rdf_renderer_media_types = list(r.media_type for r in rdf_renderer_classes)
    rdf_serializer_class = RDFSerializer

    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + rdf_renderer_classes

    def get_serializer(self, *args, **kwargs):
        if self.request.accepted_renderer.media_type in self.rdf_renderer_media_types:
            serializer_class = self.get_rdf_serializer_class()
            kwargs['context'] = self.get_rdf_serializer_context()
            return serializer_class(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def get_rdf_serializer_class(self):
        return self.rdf_serializer_class

    def get_rdf_serializer_context(self):
        return self.get_serializer_context()
