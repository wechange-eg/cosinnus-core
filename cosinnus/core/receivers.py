# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from cosinnus.conf import settings
from cosinnus.core.mail import send_mail
from django.dispatch.dispatcher import receiver
from cosinnus.core.signals import user_group_join_requested,\
    user_group_join_accepted, user_group_join_declined
from django.contrib.auth import get_user_model
from django.contrib.sites.models import get_current_site
from django.utils.encoding import force_text

#send_mail

def _mail_print(to, subject, template, data, from_email=None, bcc=None):
    print ">> Mail printing:"
    print ">> To: ", to
    print ">> Subject: ", force_text(subject)
    print ">> Body:"
    print render_to_string(template, data)
    
def send_mail_or_fail(to, subject, template, data, from_email=None, bcc=None):
    try:
        send_mail(to, subject, template, data, from_email, bcc)
    except:
        # FIXME: fail silently. better than erroring on the user. should be logged though!
        if settings.DEBUG:
            _mail_print(to, subject, template, data, from_email, bcc)
    

def _get_common_mail_context(request, group=None, user=None):
    """ Collects common context variables for Email templates """
    
    site = get_current_site(request)
    context = {
        'site': site,
        'site_name': site.name,
        'protocol': request.is_secure() and 'https' or 'http'
    }
    if group:
        context.update({
            'group_name': group.name,
            'group': group,
        })
    if user:
        context.update({
            'user_name': user.get_full_name() or user.get_username(),
            'user': user,
        })
    return context
        

@receiver(user_group_join_requested)
def send_group_join_request_mail(sender, group, user, **kwargs):
    for admin in get_user_model()._default_manager.filter(id__in=group.admins):
        context = _get_common_mail_context(sender.request, group=group, user=user)
        subject = _('%(group_name)s: %(user_name)s wants to join the group on %(site_name)s!')
        send_mail_or_fail(admin.email, subject % context, 'cosinnus/mail/user_group_join_requested.html', context)
                
                
@receiver(user_group_join_accepted)
def send_group_join_accepted_mail(sender, group, user, **kwargs):
    context = _get_common_mail_context(sender.request, group=group, user=user)
    subject = _('%(group_name)s: Your membership request has been accepted on %(site_name)s!')
    send_mail_or_fail(user.email, subject % context, 'cosinnus/mail/user_group_join_accepted.html', context)

                
@receiver(user_group_join_declined)
def send_group_join_declined_mail(sender, group, user, **kwargs):
    context = _get_common_mail_context(sender.request, group=group, user=user)
    subject = _('%(group_name)s: Your membership request has been declined on %(site_name)s.')
    send_mail_or_fail(user.email, subject % context, 'cosinnus/mail/user_group_join_declined.html', context)

