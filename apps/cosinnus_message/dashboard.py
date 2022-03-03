# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget

from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user

from cosinnus.conf import settings
from django.urls.base import reverse
from cosinnus_message.utils.utils import get_rocketchat_group_embed_url_for_user


class EmbeddedRocketchatDashboardWidget(DashboardWidget):

    app_name = 'message'
    form_class = None
    model = None
    title = _('Chat')
    user_model_attr = None  # No filtering on user page
    widget_name = 'embeddedchat'
    widget_template_name = 'cosinnus_message/widgets/message_widget.html'
    template_name = 'cosinnus_message/widgets/embedded_rocketchat_widget.html'
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        rocketchat_room_embed_url = get_rocketchat_group_embed_url_for_user(self.config.group, self.request.user)
        data = {
            'rocketchat_room_embed_url': rocketchat_room_embed_url,
            'group': self.config.group,
        }
        return (render_to_string(self.template_name, data), 0, 0)
    
    @property
    def title_url(self):
        return reverse('cosinnus:message-write-group', kwargs={'slug': self.config.group.slug})
