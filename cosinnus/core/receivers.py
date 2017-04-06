# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from cosinnus.core.mail import send_mail_or_fail, get_common_mail_context
from django.dispatch.dispatcher import receiver
from cosinnus.core.signals import user_group_join_requested,\
    user_group_join_accepted, user_group_join_declined, user_group_invited
from django.contrib.auth import get_user_model

""" 
# This signal is now being used and configured via cosinnus_notifications.py
@receiver(user_group_join_requested)
def send_group_join_request_mail(sender, group, user, **kwargs):
    for admin in get_user_model()._default_manager.filter(id__in=group.admins):
        context = get_common_mail_context(sender.request, group=group, user=user)
        subject = _('%(user_name)s wants to join %(team_name)s on %(site_name)s!')
        send_mail_or_fail(admin.email, subject % context, 'cosinnus/mail/user_group_join_requested.html', context)
                
@receiver(user_group_join_accepted)
def send_group_join_accepted_mail(sender, group, user, **kwargs):
    context = get_common_mail_context(sender.request, group=group, user=user)
    subject = _('Your membership request for %(team_name)s has been accepted on %(site_name)s!')
    send_mail_or_fail(user.email, subject % context, 'cosinnus/mail/user_group_join_accepted.html', context)
                
@receiver(user_group_join_declined)
def send_group_join_declined_mail(sender, group, user, **kwargs):
    context = get_common_mail_context(sender.request, group=group, user=user)
    subject = _('Your membership request for %(team_name)s has been declined on %(site_name)s.')
    send_mail_or_fail(user.email, subject % context, 'cosinnus/mail/user_group_join_declined.html', context)
                
@receiver(user_group_invited)
def send_user_group_invited_mail(sender, group, user, **kwargs):
    context = get_common_mail_context(sender.request, group=group, user=user)
    subject = _('You have been invited to join "%(team_name)s" on %(site_name)s.')
    send_mail_or_fail(user.email, subject % context, 'cosinnus/mail/user_group_invited.html', context)
"""
