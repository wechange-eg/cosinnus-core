from rest_framework.renderers import JSONRenderer

from cosinnus import VERSION as COSINNUS_VERSION
from django.utils.timezone import now
from cosinnus.utils.dates import timestamp_from_datetime


class CosinnusAPIFrontendJSONResponseRenderer(JSONRenderer):
    # media_type = 'text/plain'
    # media_type = 'application/json'
    charset = "utf-8"
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """  add a predictable wrapper for all JSON response data """
        wrapped_data = {
            "data": data,
            "version": COSINNUS_VERSION, #"1.0.3"  split by '.' ==> 3 items
            "timestamp": timestamp_from_datetime(now()), # unix seconds as float
        }
        return super().render(wrapped_data, accepted_media_type=accepted_media_type, renderer_context=renderer_context)