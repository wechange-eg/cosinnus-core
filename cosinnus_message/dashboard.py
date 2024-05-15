# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django import forms
from django.template.loader import render_to_string
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.utils.dashboard import DashboardWidget
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException
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
        """Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
        if has_more == False, the receiving widget will assume no further data can be loaded.
        """
        try:
            rocketchat_room_embed_url = get_rocketchat_group_embed_url_for_user(self.config.group, self.request.user)
            rocketchat_down_msg = None
        except RocketChatDownException:
            logging.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
            rocketchat_room_embed_url = None
            rocketchat_down_msg = RocketChatConnection.ROCKET_CHAT_DOWN_USER_MESSAGE
        except Exception as e:
            logging.exception(e)
            rocketchat_room_embed_url = None
            rocketchat_down_msg = RocketChatConnection.ROCKET_CHAT_EXCEPTION_USER_MESSAGE
        data = {
            'rocketchat_room_embed_url': rocketchat_room_embed_url,
            'rocket_down_msg': rocketchat_down_msg,
            'group': self.config.group,
            'show_roadblock': settings.COSINNUS_ROCKET_GROUP_WIDGET_SHOW_ROADBLOCK,
            'user': self.request.user,
        }
        return (render_to_string(self.template_name, data), 0, 0)

    @property
    def title_url(self):
        return reverse('cosinnus:message-write-group', kwargs={'slug': self.config.group.slug})
