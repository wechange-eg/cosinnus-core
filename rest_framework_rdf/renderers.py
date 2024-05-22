from rdflib import Graph
from rest_framework.renderers import BaseRenderer
from rest_framework.utils import encoders


class TurtleRenderer(BaseRenderer):
    """
    Renderer which serializes to JSON.
    """

    media_type = 'application/x-turtle'
    format = 'turtle'
    encoder_class = encoders.JSONEncoder
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into turtle, returning a bytestring.
        """
        if data is None:
            return bytes()

        # FIXME: For now only detail views are supported
        if renderer_context.get('kwargs', {}).get('pk'):
            g = Graph()
            for prefix, namespace in data.get('prefixes', {}).items():
                g.bind(prefix, namespace)

            if data.get('type'):
                g.add(data['type'])
            for resource_triple in data.get('resources', []):
                g.add(resource_triple)
            return g.serialize(format='turtle')
        else:
            return bytes()
