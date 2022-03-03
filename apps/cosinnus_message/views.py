# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import six

from django.urls import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect


from cosinnus.models.group import CosinnusGroup
from cosinnus_message.rocket_chat import RocketChatConnection
from postman.views import ConversationView, MessageView, csrf_protect_m,\
    login_required_m, _get_referer
from django.views.generic import TemplateView
from django.views.generic.base import View
from postman.models import Message
from django.http.response import Http404
from django.contrib import messages
from django.shortcuts import redirect
from cosinnus.utils.urls import safe_redirect
from django.contrib.auth import get_user_model

try:
    from django.utils.timezone import now  # Django 1.4 aware datetimes
except ImportError:
    from datetime import datetime
    now = datetime.now
from django.utils.translation import ugettext_lazy as _
from cosinnus.conf import settings


User = get_user_model()


class CosinnusMessageView(MessageView):
    """Display one specific message."""
    
    def get_context_data(self, **kwargs):
        """ clear the body text, do not quote the message when replying """
        context = super(CosinnusMessageView, self).get_context_data(**kwargs)
        if context['form']:
            context['form'].initial['body'] = None
        return context


class CosinnusConversationView(ConversationView):
    """Display a conversation."""
    
    def get_context_data(self, **kwargs):
        """ clear the body text, do not quote the message when replying """
        context = super(CosinnusConversationView, self).get_context_data(**kwargs)
        if context['form']:
            context['form'].initial['body'] = None
        return context


class UpdateMessageMixin(object):
    """
    Code common to the archive/delete/undelete actions.

    Attributes:
        ``field_bit``: a part of the name of the field to update
        ``success_msg``: the displayed text in case of success
    Optional attributes:
        ``field_value``: the value to set in the field
        ``success_url``: where to redirect to after a successful POST

    """
    http_method_names = ['post']
    field_value = None
    field_bit = None
    recipient_only_field_bit = None
    success_url = None

    @csrf_protect_m
    @login_required_m
    def dispatch(self, *args, **kwargs):
        return super(UpdateMessageMixin, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        next_url = _get_referer(request) or 'postman_inbox'
        
        """ This is all we wanted to do that we needed to override the postman views for """
        pks = request.POST.get('pks', None)
        if pks is None:
            pks = [k.split('__')[1] for k,v in list(request.POST.items()) if 'delete_pk' in k and v=='true']

        tpks = request.POST.get('tpks', None)
        if tpks is None:
            tpks = [k.split('__')[1] for k,v in list(request.POST.items()) if 'delete_tpk' in k and v=='true']
        
        if pks or tpks:
            user = request.user
            filter = Q(pk__in=pks) | Q(thread__in=tpks)
            if self.recipient_only_field_bit:
                recipient_rows = Message.objects.as_recipient(user, filter).update(**{self.recipient_only_field_bit: self.field_value})
            else:
                recipient_rows = Message.objects.as_recipient(user, filter).update(**{'recipient_{0}'.format(self.field_bit): self.field_value})
                sender_rows = Message.objects.as_sender(user, filter).update(**{'sender_{0}'.format(self.field_bit): self.field_value})
            if not (recipient_rows or sender_rows):
                raise Http404  # abnormal enough, like forged ids
            messages.success(request, self.success_msg, fail_silently=True)
            next_url = request.GET.get('next', None)
            next_url = safe_redirect(next_url, request) if next_url else None
            return redirect(next_url or self.success_url or request.META.get('HTTP_REFERER', reverse('postman:inbox')))
        else:
            messages.warning(request, _("Select at least one object."), fail_silently=True)
            return redirect(next_url)


class ArchiveView(UpdateMessageMixin, View):
    """Mark messages/conversations as archived."""
    field_bit = 'archived'
    success_msg = _("Messages or conversations successfully archived.")
    field_value = True


class DeleteView(UpdateMessageMixin, View):
    """Mark messages/conversations as deleted."""
    field_bit = 'deleted_at'
    success_msg = _("Messages or conversations successfully deleted.")
    field_value = now()


class MarkAsReadView(UpdateMessageMixin, View):
    """Mark messages/conversations as read."""
    recipient_only_field_bit = 'read_at'
    success_msg = _("Messages were marked as read.")
    field_value = now()


class UndeleteView(UpdateMessageMixin, View):
    """Revert messages/conversations from marked as deleted."""
    field_bit = 'deleted_at'
    success_msg = _("Messages or conversations successfully recovered.")


def index(request, *args, **kwargs):
    return HttpResponseRedirect(reverse('postman-index'))


class BaseRocketChatView(TemplateView):

    template_name = 'cosinnus_message/rocket_chat.html'
    base_url = settings.COSINNUS_CHAT_BASE_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url'] = self.get_rocket_chat_url()
        return context

    def get_rocket_chat_url(self):
        path = self.request.GET.get('path')
        if path == '/':
            path = None
        return f'{self.base_url}/{path}' if path else self.base_url


class RocketChatIndexView(BaseRocketChatView):

    pass


class RocketChatWriteView(BaseRocketChatView):

    def get_rocket_chat_url(self):
        user = None
        username = self.kwargs.get('username')
        if username:
            user = get_user_model().objects.filter(username=username).first()
        if user:
            profile = user.cosinnus_profile
            if not profile:
                return self.base_url
            return f'{self.base_url}/direct/{profile.rocket_username}/'
        else:
            return self.base_url


class RocketChatWriteGroupView(BaseRocketChatView):

    queryset = None # inited as CosinnusGroup.objects.all_in_portal() on __init__
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = CosinnusGroup.objects.all_in_portal()

    def get_object(self):
        slug = self.kwargs.get('slug')
        if slug:
            return self.queryset.get(slug=slug)
        return

    def get_rocket_chat_url(self):
        """
        Returns Rocket.Chat group URL with user is member of group,
        creates a new private group with group admins if not
        :return:
        """
        group = self.get_object()
        if not group:
            return self.base_url
        user = self.request.user
        group_name = ''
        if user and user.is_authenticated:
            rocket = RocketChatConnection()
            group_name = rocket.groups_request(group, user, force_sync_membership=True)

        if group_name:
            return f'{self.base_url}/group/{group_name}/'
        return self.base_url
