# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import range
from builtins import object
import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django_mailbox.models import Message
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from postman.models import Message as PostmanMessage
from postman.utils import format_subject

from cosinnus.core.mail import send_mail_or_fail_threaded
from cosinnus_message.forms import CustomReplyForm, CustomWriteForm
from cosinnus.models.group import CosinnusPortal

from cosinnus_message.models import CosinnusMailbox
from django.core.exceptions import MultipleObjectsReturned
from postman.views import RestrictRecipientMixin

logger = logging.getLogger('cosinnus')


DIRECT_REPLY_ADDRESSEE = re.compile(r'directreply\+([0-9]+)\+([a-zA-Z0-9]+)[@+]', re.IGNORECASE)
EMAIL_RE = re.compile(
    r"([-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?', re.IGNORECASE)  # domain


def update_mailboxes():
    """ Downloads all mail from the SMTP/IMAP accounts from Mailboxes assigned to this portal """
    
    mailboxes = CosinnusMailbox.active_mailboxes.filter(portal=CosinnusPortal.get_current())
    if len(mailboxes) == 0:
        return
    
    for mailbox in mailboxes:
        try:
            messages = mailbox.get_new_mail()
        except Exception as e:
            logger.error('Error trying to collect directreply mails for portal %s' % CosinnusPortal.get_current().slug,
                         extra={'exception': force_text(e)})
            
        logger.info('Successfully gathered directreply messages for portal %s' % CosinnusPortal.get_current().slug,
                    extra={'number_messages': len(messages)})
        
        """
        for message in messages:
            logger.info(
                'Received %s (from %s)',
                message.subject,
                message.from_address
            )
        """

def process_direct_reply_messages(messages=None, no_delete=False):
    """ Will check all existing django_mail Messages:
        - drop all mail not containing this Pattern in the body text: directreply+<portal-id>+<hash>+<mailbox-domain> 
        - take all mail for this portal. 
            - if there is a hash matching a postman message, match sender to user, reply as that user using body text
            - delete the mail, no matter if a match was found or not
        - retain the rest (other portals might be using the same mailbox)
        """
    messages_to_delete = []
    USER_MODEL = get_user_model()
    
    if messages is not None:
        all_messages = messages
    else:
        # order by date incoming, ascending to not confuse order for consecutive messages
        all_messages = Message.objects.all().order_by('read') 
    
    for message in all_messages:
        match = DIRECT_REPLY_ADDRESSEE.search(message.text)
        
        # get sender email
        from_email_match = EMAIL_RE.search(message.from_header)
        if not from_email_match or not from_email_match.group(): 
            messages_to_delete.append(message)
            continue
        replier_email = from_email_match.group()
        
        # get and clean message body
        text = message.text or ''
        text = clean_reply_message_quotation(text)
        
        # message is spam or unrelated to direct messages: remove it
        if not match or not len(match.groups()) == 2:
            messages_to_delete.append(message)
            logger.info('A directreply-received message did not contain a directreply code.', extra={'message-from': message.from_header, 'message-text': message.text, 'portal-id': CosinnusPortal.get_current().id})
            send_direct_reply_error_mail(replier_email, text, _('Your reply could not be matched to an existing message.'))
            continue
        
        portal_id, hash = match.groups()
        portal_id = int(portal_id)
        logger.info('A directreply-received message was matched with a directreply code.', extra={'message-from': message.from_header, 'message-text': message.text, 'portal-id': CosinnusPortal.get_current().id, 'hash': hash, 'parsed-portal-id': portal_id})
        if not portal_id == CosinnusPortal.get_current().id:
            # message is not for this portal, retain message for other portals
            logger.info('A directreply-received message was matched for a different portal and is being retained.', extra={'message-from': message.from_header, 'message-text': message.text, 'portal-id': CosinnusPortal.get_current().id, 'hash': hash, 'parsed-portal-id': portal_id})
            continue
        
        # from now we either process the message or not, but we definitely delete it, so:
        messages_to_delete.append(message)
        
        # try to find a postman message with the hash from this addressee
        try:
            postman_message = PostmanMessage.objects.get(direct_reply_hash=hash)
        except PostmanMessage.DoesNotExist:
            logger.info('A directreply-received message was matched, but a postman message could not be found with that hash.', extra={'message-from': message.from_header, 'message-text': message.text, 'portal-id': CosinnusPortal.get_current().id, 'hash': hash, 'parsed-portal-id': portal_id})
            send_direct_reply_error_mail(replier_email, text, _('Your reply could not be matched to an existing message.'))
            continue
        except MultipleObjectsReturned:
            logger.error('A directreply-received message was matched, but more than 1 postman message were be found with that hash.', extra={'message-from': message.from_header, 'message-text': message.text, 'portal-id': CosinnusPortal.get_current().id, 'hash': hash, 'parsed-portal-id': portal_id})
            send_direct_reply_error_mail(replier_email, text, _('An internal error occured.'))
            continue
        
        # try to find the sender email in the user accounts
        sender_email_bad = False
        try:
            user = USER_MODEL.objects.get(is_active=True, email__iexact=replier_email)
        except USER_MODEL.DoesNotExist:
            sender_email_bad = True
        
        # make sure the sender of the reply is really the recipient of the replied-to message!
        # if this doesn't match, likely a valid user just replied from the wrong email account, so we send them an error message back
        if sender_email_bad or not user == postman_message.recipient:
            send_direct_reply_error_mail(replier_email, text, _('The email adress you sent the reply from is not the one associated with your user account. Please send direct replies only from the email adress you are registered with on the site!'))
            continue
        
        # Forum group messages can only be replied to by superusers
        checkMixin = RestrictRecipientMixin()
        if checkMixin.check_restricted_recipient(postman_message, user):
            send_direct_reply_error_mail(replier_email, text, _('Only Administrators may send a message to this project/group!'))
            continue
        
        # error out on empty texts
        successfully_replied = False
        if text and text.strip():
            # emulate the user sending a postman message
            successfully_replied = reply_to_postman_message(postman_message, user, text)
        
        if not successfully_replied:
            send_direct_reply_error_mail(replier_email, text, _('There was an error when processing your message text!'))
            continue
        logger.info('Direct reply successfully processed.')
        
    if not no_delete and not getattr(settings, 'DEBUG_LOCAL', False):
        Message.objects.filter(id__in=[m.id for m in messages_to_delete]).delete()
   

def clean_reply_message_quotation(text):
    """ Attempts to clean out all previous quoted email fragments from an email text-only body text. """
    had_reply = False
    
    lines = text.split('\n')
    clean_lines = []
    
    # aggressively remove all lines after the first reply-quote character
    for line in lines:
        if line.startswith('>'):
            break
        clean_lines.append(line)
    
    if len(clean_lines) < len(lines):
        # we have removed a reply, mark this!
        had_reply = True
        
    # remove empty beginning and trailing lines
    def _remove_empty_trailing_lines_till_text(_lines):
        if not _lines: return _lines
        for index in reversed(range(len(_lines))):
            if len(_lines[index].strip()) == 0:
                del _lines[index]
            else:
                break
        return _lines
    clean_lines = _remove_empty_trailing_lines_till_text(clean_lines)
    clean_lines = list(reversed(_remove_empty_trailing_lines_till_text(list(reversed(clean_lines)))))
    
    # if we removed a reply, we may now delete the last line, if it ends with a ':'
    # that is the gmail client way of saying "On <date>, <sender> wrote:"
    if clean_lines and had_reply:
        if clean_lines[-1].strip().endswith(':'):
            del clean_lines[-1]
            clean_lines = _remove_empty_trailing_lines_till_text(clean_lines)
    
    text = '\n'.join(clean_lines) 
    return text
    
    
def reply_to_postman_message(message, user, text):    
    """ Sends a reply to a postman message with a given text, from a given user.
        @param message: The postman message to reply to (usually the last message in the thread that is not from `user`)
        @param user: The replying user as User model 
        @param text: The text-only body text of the reply. 
        @param return: True if successful, else False """
        
    if message.multi_conversation:
        recipients = ['user:%d' % rec.id for rec in message.multi_conversation.participants.all()]
    else:
        recipients = []
    kwargs = {
       'initial': {},
       'recipient': message.sender,
       'sender': user,
       'site': CosinnusPortal.get_current().site,
       'data': MultiValueDict({
           'body': [text],
           'subject': [message.quote(format_subject)['subject']],
           'reply_all': '1',
           'recipients': recipients,
       }),
    }
    
    # TODO: fixme: really the default should be '0' for reply single on directreply. 
    # like this it actually sucks because spam. what do?
    # the email should explain this, as well!!!
    # also, if we reply single, we need to change the reply_copy_mode code, so that
    # we answer to message.parent and not message.thread, because in the email, the thread
    
    # or we could completely disable directreply in conversations, which would suck
    
    form = CustomReplyForm(**kwargs)
    if form.is_valid():
        form.save(parent=message)
        return True
    else:
        logger.warning('Could not direct-reply to a postman message, because the form was invalid!', extra={'form-errors': force_text(form.errors), 'wechange-user-email': user.email, 'text': text})
        return False


def write_postman_message(user, sender, subject, text):
    """ When you want to directly create a postman message as if sent from one user to another.
        Will not trigger a notification being sent. 
        @param user: The recipient user as User model
        @param sender: The sending user as User model 
        @param subject: The text-only subject text of the message.
        @param text: The text-only body text of the message. 
        @param return: True if successful, else False """
    if len(subject) > PostmanMessage.SUBJECT_MAX_LENGTH:
        subject = subject[:PostmanMessage.SUBJECT_MAX_LENGTH]
    kwargs = {
       'initial': {},
       'sender': sender,
       'site': CosinnusPortal.get_current().site,
       'data': MultiValueDict({
           'recipients': ['user:%d' % user.id],
           'body': [text],
           'subject': [subject],
       }),
       'do_not_notify_users': True,
    }
    form = CustomWriteForm(**kwargs)
    if form.is_valid():
        form.save()
        return True
    else:
        logger.warning('Could not direct-write a postman message, because the form was invalid!', extra={'form-errors': force_text(form.errors), 'sender-user-email': user.email, 'text': text})
        return False
    
    
def send_direct_reply_error_mail(recipient_email, text, reason):
    subject = _('Your direct reply failed!')
    template = 'cosinnus_message/email_direct_reply_failed.txt'
    logger.warning('Sending out a direct-reply error mail', extra={'recipient': recipient_email, 'reason': reason, 'text': text})
    send_mail_or_fail_threaded(recipient_email, subject, template, {'reason': reason, 'text': text})


def _test_postman_reply(direct_reply_hash, user_email, test_text):
    """ Internal purposes only """
    msg = PostmanMessage.objects.get(direct_reply_hash=direct_reply_hash)
    user = get_user_model().objects.get(email=user_email)
    return reply_to_postman_message(msg, user, test_text)


def _test_direct_reply_mail(sender_email=None, body_text=None):
    """ Internal purposes only """
    class Msg(object):
        from_header = sender_email or 'testuser83@nowhere.com'
        text = body_text or """
            > --------------------------------------------------------------------
            > DIRECT-REPLY CODE: 
            > directreply+1+VYEVjxComiYWZ95a7Vj3FJ3VadWzQ58C+wachstumswende.de 
            -------------------------------------------------------------------------------
        """
    process_direct_reply_messages([Msg()], True)
    

def get_rocketchat_group_embed_url_for_user(group, user):
    """ Returns the iframe-embeddable URL for an only-group-chat view for a CosinnusGroup for
        a user if the user is a member of it, None otherwise """
    
    if user and user.is_authenticated and group.is_member(user):
        from cosinnus_message.rocket_chat import RocketChatConnection
        rocket = RocketChatConnection()
        group_name = rocket.get_group_room_name(group)
        if group_name:
            return f'{settings.COSINNUS_CHAT_BASE_URL}/group/{group_name}?layout=embedded'
    return None


def get_rocketchat_mail_notification_setting_from_user_preference(user):
    """ Retrieves the rocketchat user email preference and returns one value of
        `GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES`.
        Since there are only two values, unless we specifically see that a user's settings
        is set to off, we assume that it is set to Mentions, because that's what rocketchat does as default """
    from cosinnus.models.profile import GlobalUserNotificationSetting
    from cosinnus_message.rocket_chat import (RocketChatConnection, 
        ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_OFF) 
    pref = RocketChatConnection().get_user_email_preference(user)
    setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS
    if pref and pref == ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_OFF:
        setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF
    return setting

def save_rocketchat_mail_notification_preference_for_user_setting(user, setting):
    """ Saves the rocketchat email preference given the user setting from
        `GlobalUserNotificationSetting.ROCKETCHAT_SETTING_CHOICES`
        @return: True if successful, False if not """
    from cosinnus.models.profile import GlobalUserNotificationSetting
    from cosinnus_message.rocket_chat import (RocketChatConnection, 
        ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_OFF, 
        ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_MENTIONS) 
    setting_map = {
        GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF: ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_OFF,
        GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS: ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_MENTIONS,
    }
    pref = setting_map.get(setting)
    success = RocketChatConnection().set_user_email_preference(user, pref)
    return success
