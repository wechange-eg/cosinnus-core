# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import join

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import simplejson
from django.utils.translation import ugettext as _

from dajaxice.decorators import dajaxice_register

from cosinnus.core.mail import send_mail
from cosinnus.models.group import GroupAdmin
from cosinnus.templatetags.cosinnus import full_name


@dajaxice_register
def join_request(request, groupid, userid):
    """Sends an email with the user name that wants to join the given group to the administrators"""
    user = get_user_model().objects.get(pk=int(userid))
    group = Group.objects.get(pk=int(groupid))

    user_name = full_name(user)
    group_name = group.name

    # send email to the administrators of the group
    subject = _('The user %(user_name)s wants to join the group %(group_name)s') % {
        'user_name': user_name,
        'group_name': group_name,
    }
    template = join('notify', 'mail', 'group_join_request.txt')

    group_admins = GroupAdmin.objects.filter(group=group)
    join_request_was_sent = False
    admins_found = False
    for group_admin in group_admins:
        admins_found = True
        data = {
            'admin_name': full_name(group_admin.user),
            'user_name': user_name,
            'group_name': group_name,
        }

        try:
            send_mail(group_admin.user.email, subject, template, data)
            join_request_was_sent = True
        except Exception as e:  # TODO fix
            if e.args[0] == 111:
                exception_message = _('Communication with the email server failed.')
            else:
                exception_message = e.args[1]

    if admins_found:
        if join_request_was_sent:
            title = _('Request sent')
            message = _('Your join request was sent to the administrator(s) of the group.')
        else:
            title = _('Request failed')
            message = _('Your join request could not be sent! Reason: ') + exception_message
    else:
        title = _('Request failed, no administrators')
        message = _(
            'Your join request could not be sent because there are no administrators in the group %(group_name)s.'
        ) % {
            'group_name': group_name,
        }

    return simplejson.dumps({
        'success': join_request_was_sent,
        'title': title,
        'message': message,
    })
