from __future__ import unicode_literals
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.permissions import check_user_can_receive_emails
from cosinnus.core.mail import send_mail_or_fail_threaded
from importlib import import_module
import re
import sys
from textwrap import TextWrapper

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.translation import gettext, gettext_lazy as _

# make use of a favourite notifier app such as django-notification
# but if not installed or not desired, fallback will be to do basic emailing
name = getattr(settings, 'POSTMAN_NOTIFIER_APP', 'notification')
if name and name in settings.INSTALLED_APPS:
    name = name + '.models'
    notification = import_module(name)
else:
    notification = None

# give priority to a favourite mailer app such as django-mailer
# but if not installed or not desired, fallback to django.core.mail
name = getattr(settings, 'POSTMAN_MAILER_APP', 'mailer')
if name and name in settings.INSTALLED_APPS:
    send_mail = import_module(name).send_mail
else:
    from django.core.mail import send_mail

# to disable email notification to users
DISABLE_USER_EMAILING = getattr(settings, 'POSTMAN_DISABLE_USER_EMAILING', False)

# default wrap width; referenced in forms.py
WRAP_WIDTH = 55


def format_body(sender, body, indent=_("> "), width=WRAP_WIDTH):
    """
    Wrap the text and prepend lines with a prefix.

    The aim is to get lines with at most `width` chars.
    But does not wrap if the line is already prefixed.

    Prepends each line with a localized prefix, even empty lines.
    Existing line breaks are preserved.
    Used for quoting messages in replies.

    """
    indent = force_str(indent)  # join() doesn't work on lists with lazy translation objects ; nor startswith()
    wrapper = TextWrapper(width=width, initial_indent=indent, subsequent_indent=indent)
    # rem: TextWrapper doesn't add the indent on an empty text
    quote = '\n'.join([line.startswith(indent) and indent+line or wrapper.fill(line) or indent for line in body.splitlines()])
    return gettext("\n\n{sender} wrote:\n{body}\n").format(sender=sender, body=quote)


def format_subject(subject, old_style=False):
    """
    Prepend a pattern to the subject, unless already there.

    Matching is case-insensitive.

    """
    
    if old_style:
        str = gettext("Re: {subject}")
        pattern = '^' + str.replace('{subject}', '.*') + '$'
        return subject if re.match(pattern, subject, re.IGNORECASE) else str.format(subject=subject)
    else:
        return subject

def email(subject_template, message_template, recipient_list, object, action, site):
    """Compose and send an email."""
    ctx_dict = {'site': site, 'object': object, 'action': action}
    subject = render_to_string(subject_template, ctx_dict)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    # check if we have a connected mailbox for direct replies, and if so, set the sender to a specified email, so that users
    # can directly reply to them
    hash_vars = {
        'portal_name': force_str(_(settings.COSINNUS_BASE_PAGE_TITLE_TRANS)),
        'default_from': settings.DEFAULT_FROM_EMAIL,
    }
    if CosinnusPortal.get_current().mailboxes.filter(active=True).count() > 0:
        hash_vars.update({
            'domain': settings.DEFAULT_FROM_EMAIL.split('@')[1],
            'portal_id': CosinnusPortal.get_current().id,
            'hash': object.direct_reply_hash,
        })
        sender = '%(portal_name)s <directreply@%(domain)s>' % hash_vars
        hash_code = 'directreply+%(portal_id)d+%(hash)s+%(domain)s' % hash_vars
        ctx_dict.update({
            'direct_reply_enabled': True,
            'hash_code': hash_code,
        })
    else:
        sender = '%(portal_name)s <%(default_from)s>' % hash_vars
        
    #message = render_to_string(message_template, ctx_dict)
    # during the development phase, consider using the setting: EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    #send_mail(subject, message, sender, recipient_list, fail_silently=True)
    
    # now sending through our system
    send_mail_or_fail_threaded(recipient_list[0], subject, message_template, ctx_dict, sender, is_html=False)

def email_visitor(object, action, site):
    """Email a visitor."""
    email('postman/email_visitor_subject.txt', 'postman/email_visitor.txt', [object.email], object, action, site)


def notify_user(object, action, site):
    """Notify a user."""
    if action == 'rejection':
        user = object.sender
        label = 'postman_rejection'
    elif action == 'acceptance':
        user = object.recipient
        parent = object.parent
        label = 'postman_reply' if (parent and parent.sender_id == object.recipient_id) else 'postman_message'
    else:
        return
    if notification:
        # the context key 'message' is already used in django-notification/models.py/send_now() (v0.2.0)
        notification.send(users=[user], label=label, extra_context={'pm_message': object, 'pm_action': action})
    else:
        if not DISABLE_USER_EMAILING and user.email and user.is_active and check_user_can_receive_emails(user):
            email('postman/email_user_subject.txt', 'postman/email_user.txt', [user.email], object, action, site)
