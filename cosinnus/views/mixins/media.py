# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.template.loader import render_to_string


class VideoEmbedFieldMixin(object):
    """
    Extracts Video-Types and Video-Ids from a URL-Field so they can be embedded.
    """
    
    video_url_field_name = 'video'
    video_embed_template = 'cosinnus/common/embed_video_field.html'
    
    def __init__(self, *args, **kwargs):
        if not self.video_url_field_name:
            raise ImproperlyConfigured('``video_url_field_name`` needs to be set for VideoEmbedFieldMixin!')
        
        return super(VideoEmbedFieldMixin, self).__init__(*args, **kwargs)
    
    def get_video_properties(self, video=None):
        """ Returns a dict specific for the ``media.html`` widget that contains the properties
            required for an embed code, parsed from the given URL 
            @param video: If supplied, will parse from this value instead of the video field of the class """
        video = video or getattr(self, self.video_url_field_name, None)
        if not video:
            return {}
        try:
            match = re.search(r'^(https://)?(www\.)?(vimeo\.com/)?(\d+)', video)
            if match:
                # VIMEO
                return {'vimeoid': match.group(4)}
            else:
                # ASSUMING YOUTUBE
                match = re.search(r'[?&]v=([a-zA-Z0-9-_]+)(&|$)', video)
                if not match:
                    match = re.search(r'youtu.be/([a-zA-Z0-9-_]+)(&|$)', video)
                if match:
                    return {'youtubeid': match.groups()[0]}
                return {}
        except:
            """ Pokemon exception handling """
            if settings.DEBUG:
                raise
            return {'error': video}
        return {}
    
    def render_video_embed(self):
        return render_to_string(self.video_embed_template, dictionary=self.get_video_properties())
    