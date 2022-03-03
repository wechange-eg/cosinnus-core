from __future__ import unicode_literals
from __future__ import division
from builtins import str
from builtins import object
import hashlib
from django.utils.crypto import get_random_string
from cosinnus.models.tagged import AttachableObjectModel, LastVisitedMixin
from importlib import import_module
import six

from cosinnus.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.db.models.query import QuerySet
from django.utils.encoding import force_text
try:
    from django.utils.text import Truncator  # Django 1.4
except ImportError:
    from postman.future_1_4 import Truncator
try:
    from django.utils.timezone import now  # Django 1.4 aware datetimes
except ImportError:
    from datetime import datetime
    now = datetime.now
from django.utils.translation import ugettext, ugettext_lazy as _

from . import OPTION_MESSAGES
from .query import PostmanQuery
from .utils import email_visitor, notify_user
import uuid

def get_uuid():
    return uuid.uuid4().hex

# moderation constants
STATUS_PENDING = 'p'
STATUS_ACCEPTED = 'a'
STATUS_REJECTED = 'r'
STATUS_CHOICES = (
    (STATUS_PENDING, _('Pending')),
    (STATUS_ACCEPTED, _('Accepted')),
    (STATUS_REJECTED, _('Rejected')),
)
# ordering constants
ORDER_BY_KEY = 'o'  # as 'order'
ORDER_BY_FIELDS = {}  # setting is deferred in setup()
ORDER_BY_MAPPER = {'sender': 'f', 'recipient': 't', 'subject': 's', 'date': 'd'}  # for templatetags usage


def setup():
    """
    Deferred actions, that can not be done at import time since Django 1.7.
    Normally called in AppConfig.ready().
    For backwards compatibility, also called on first need.

    """
    try:
        from django.contrib.auth import get_user_model  # Django 1.5
    except ImportError:
        from postman.future_1_5 import get_user_model
    name_user_as = getattr(settings, 'POSTMAN_NAME_USER_AS', get_user_model().USERNAME_FIELD)
    ORDER_BY_FIELDS.update({
        'f': 'sender__' + name_user_as,     # as 'from'
        't': 'recipient__' + name_user_as,  # as 'to'
        's': 'subject',  # as 'subject'
        'd': 'sent_at',  # as 'date'
    })


def get_order_by(query_dict):
    """
    Return a field name, optionally prefixed for descending order, or None if not found.

    Argument:
    ``query_dict``: a dictionary to look for a key dedicated to ordering purpose

    """
    if ORDER_BY_KEY in query_dict:
        code = query_dict[ORDER_BY_KEY]  # code may be uppercase or lowercase
        if not ORDER_BY_FIELDS:  # backwards compatibility, before Django 1.7
            setup()
        order_by_field = ORDER_BY_FIELDS.get(code.lower())
        if order_by_field:
            if code.isupper():
                order_by_field = '-' + order_by_field
            return order_by_field


def get_user_representation(user):
    """
    Return a User representation for display, configurable through an optional setting.
    """
    show_user_as = getattr(settings, 'POSTMAN_SHOW_USER_AS', None)
    if isinstance(show_user_as, six.string_types):
        if '.' in show_user_as:
            mod_path, _, attr_name = show_user_as.rpartition('.')
            try:
                return force_text(getattr(import_module(mod_path), attr_name)(user))
            except:  # ImportError, AttributeError, TypeError (not callable)
                pass
        else:
            attr = getattr(user, show_user_as, None)
            if callable(attr):
                attr = attr()
            if attr:
                return force_text(attr)
    elif callable(show_user_as):
        try:
            return force_text(show_user_as(user))
        except:
            pass
    return force_text(user)  # default value, or in case of empty attribute or exception


def get_user_name(user):
    """
    Return the identifying name for a User.
    """
    name_user_as = getattr(settings, 'POSTMAN_NAME_USER_AS', None)
    if name_user_as:
        return getattr(user, name_user_as)
    return user.get_username()  # default


class MultiConversation(models.Model):
    """ A model to reference to keep track of which conversation between multiple users a message belongs to """
    
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=False,
        related_name='postman_multiconversations')
    targetted_groups = models.ManyToManyField(settings.COSINNUS_GROUP_OBJECT_MODEL, blank=True,
        related_name='+', help_text='Groups that the message has been sent to. This is kept for purely '
        'informative reasons, so we can show the user the involved groups, but will not be used for '
        'something like keeping the participants list up to date')
    
    def __str__(self):
        return 'MultiConv <%d>: %s' % (getattr(self, 'id', -1), ','.join([part.username for part in self.participants.all()]))
    

class MultiConversationModel(models.Model):
    """ To be used by Message, models the functionality of many users sharing a messages through a thread,
        even though each message has its own object for each of the participating users """
    
    class Meta(object):
        abstract = True
    
    multi_conversation = models.ForeignKey('postman.MultiConversation', null=True, blank=True, on_delete=models.CASCADE)
    level = models.IntegerField(_(''), default=0, help_text='Used to identify the Message objects belonging '
        'to a MultiConversation that belong to the same "physical" message. Unused for default 2-person conversations.')
    master_for_sender = models.BooleanField(default=True, help_text='Since in a MultiConversation, for one message '
        'there exist multiple Message objects with the same level and same sender, only one those exists with '
        'master_for_sender==True. This is the one that is checked for info like `sender_archived` and `sender_deleted_at`')
    

class MessageManager(models.Manager):
    """The manager for Message."""

    def _folder(self, related, filters, user, option=None, order_by=None):
        """Base code, in common to the folders."""
        qs = self.all() if option == OPTION_MESSAGES else QuerySet(self.model, PostmanQuery(self.model), using=self._db)
        if related:
            qs = qs.select_related(*related)
        if order_by:
            qs = qs.order_by(order_by)
        if isinstance(filters, (list, tuple)):
            lookups = models.Q()
            for filter in filters:
                lookups |= models.Q(**filter)
        else:
            lookups = models.Q(**filters)
        if option == OPTION_MESSAGES:
            qs = qs.filter(lookups)
            # Adding a 'count' attribute, to be similar to the by-conversation case,
            # should not be necessary. Otherwise add:
            # .extra(select={'count': 'SELECT 1'})
        else:
            qs = qs.extra(select={'count': '{0}.count'.format(qs.query.pm_alias_prefix)})
            qs.query.pm_set_extra(table=(
                # extra columns are always first in the SELECT query
                # for tests with the version 2.4.1 of sqlite3 in py26, add to the select: , 'id': 'postman_message.id'
                self.filter(lookups, thread_id__isnull=True).extra(select={'count': 0})\
                    .values_list('id', 'count').order_by(),
                # use separate annotate() to keep control of the necessary order
                self.filter(lookups, thread_id__isnull=False).values('thread').annotate(count=models.Count('pk')).annotate(id=models.Max('pk'))\
                    .values_list('id', 'count').order_by(),
            ))
        
        # for conversations messages where the user is the first sender (initiator), we filter so that
        # we only show him the master_for_sender messages (otherwise they would see duplicates)
        qs = qs.filter(models.Q(thread__isnull=True) | ~models.Q(thread__sender=user) | (models.Q(thread__sender=user) & models.Q(master_for_sender=True)))
        
        return qs

    def inbox(self, user, related=True, **kwargs):
        """
        Return accepted messages received by a user but not marked as archived or deleted.
        """
        related = ('sender',) if related else None
        filters = {
            'recipient': user,
            'recipient_archived': False,
            'recipient_deleted_at__isnull': True,
            'moderation_status': STATUS_ACCEPTED,
        }
        return self._folder(related, filters, user, **kwargs)

    def inbox_unread_count(self, user):
        """
        Return the number of unread messages for a user.

        Designed for context_processors.py and templatetags/postman_tags.py

        """
        return self.inbox(user, related=False, option=OPTION_MESSAGES).filter(read_at__isnull=True).count()

    def sent(self, user, **kwargs):
        """
        Return all messages sent by a user but not marked as archived or deleted.
        """
        related = ('recipient',)
        filters = {
            'sender': user,
            'sender_archived': False,
            'sender_deleted_at__isnull': True,
            'master_for_sender': True,
            # allow to see pending and rejected messages as well
        }
        return self._folder(related, filters, user, **kwargs)

    def archives(self, user, **kwargs):
        """
        Return messages belonging to a user and marked as archived.
        """
        related = ('sender', 'recipient')
        filters = ({
            'recipient': user,
            'recipient_archived': True,
            'recipient_deleted_at__isnull': True,
            'master_for_sender': True,
            'moderation_status': STATUS_ACCEPTED,
        }, {
            'sender': user,
            'sender_archived': True,
            'sender_deleted_at__isnull': True,
        })
        return self._folder(related, filters, user, **kwargs)

    def trash(self, user, **kwargs):
        """
        Return messages belonging to a user and marked as deleted.
        """
        related = ('sender', 'recipient')
        filters = ({
            'recipient': user,
            'recipient_deleted_at__isnull': False,
            'master_for_sender': True,
            'moderation_status': STATUS_ACCEPTED,
        }, {
            'sender': user,
            'sender_deleted_at__isnull': False,
        })
        return self._folder(related, filters, user, **kwargs)

    def thread(self, user, filter):
        """
        Return message/conversation for display.
        """
        return self.select_related('sender', 'recipient').filter(
            filter,
            (models.Q(recipient=user) & models.Q(moderation_status=STATUS_ACCEPTED)) | models.Q(sender=user) | models.Q(multi_conversation__participants=user),
        ).order_by('sent_at').distinct()

    def as_recipient(self, user, filter):
        """
        Return messages matching a filter AND being visible to a user as the recipient.
        """
        return self.filter(filter, recipient=user, moderation_status=STATUS_ACCEPTED)

    def as_sender(self, user, filter):
        """
        Return messages matching a filter AND being visible to a user as the sender.
        """
        return self.filter(filter, sender=user, master_for_sender=True)  # any status is fine

    def perms(self, user):
        """
        Return a field-lookups filter as a permission controller for a reply request.

        The user must be the recipient of the accepted, non-deleted, message

        """
        return models.Q(recipient=user) & models.Q(moderation_status=STATUS_ACCEPTED) & models.Q(recipient_deleted_at__isnull=True)

    def set_read(self, user, filter):
        """
        Set messages as read.
        """
        return self.filter(
            filter,
            recipient=user,
            moderation_status=STATUS_ACCEPTED,
            read_at__isnull=True,
        ).update(read_at=now())


@six.python_2_unicode_compatible
class Message(AttachableObjectModel, LastVisitedMixin, MultiConversationModel):
    """
    A message between a User and another User or an AnonymousUser.
    """

    SUBJECT_MAX_LENGTH = 120

    subject = models.CharField(_("subject"), max_length=SUBJECT_MAX_LENGTH)
    body = models.TextField(_("body"), blank=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', null=True, blank=True, verbose_name=_("sender"), on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', null=True, blank=True, verbose_name=_("recipient"), on_delete=models.CASCADE)
    email = models.EmailField(_("visitor"), blank=True)  # instead of either sender or recipient, for an AnonymousUser
    parent = models.ForeignKey('self', related_name='next_messages', null=True, blank=True, verbose_name=_("parent message"), on_delete=models.CASCADE)
    thread = models.ForeignKey('self', related_name='child_messages', null=True, blank=True, verbose_name=_("root message"), on_delete=models.CASCADE)
    sent_at = models.DateTimeField(_("sent at"), default=now)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    replied_at = models.DateTimeField(_("replied at"), null=True, blank=True)
    sender_archived = models.BooleanField(_("archived by sender"), default=False)
    recipient_archived = models.BooleanField(_("archived by recipient"), default=False)
    sender_deleted_at = models.DateTimeField(_("deleted by sender at"), null=True, blank=True)
    recipient_deleted_at = models.DateTimeField(_("deleted by recipient at"), null=True, blank=True)
    # moderation fields
    moderation_status = models.CharField(_("status"), max_length=1, choices=STATUS_CHOICES, default=STATUS_PENDING)
    moderation_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='moderated_messages',
        null=True, blank=True, verbose_name=_("moderator"), on_delete=models.CASCADE)
    moderation_date = models.DateTimeField(_("moderated at"), null=True, blank=True)
    moderation_reason = models.CharField(_("rejection reason"), max_length=120, blank=True)
    
    # used as a reply-address for a catchall mailbox to reply by email 
    direct_reply_hash = models.CharField(max_length=50, verbose_name=_('Direct Reply Hash'),
         blank=True, null=True)

    objects = MessageManager()

    class Meta(object):
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ['-sent_at', '-id']

    def __str__(self):
        return "{0}:: {1}>{2}:{3}".format(self.id, self.obfuscated_sender, self.obfuscated_recipient, Truncator(self.subject).words(5))
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-envelope'
    
    def save(self, *args, **kwargs):
        if not getattr(self, 'id', None):
            self.direct_reply_hash = get_random_string(32)
        super(Message, self).save(*args, **kwargs)
    
    def get_absolute_url(self):
        "Usage is deprecated since v3.3.0, because it doesn't integrate well with the addition of namespaces."
        return reverse('postman:view', args=[self.pk])

    def is_pending(self):
        """Tell if the message is in the pending state."""
        return self.moderation_status == STATUS_PENDING
    def is_rejected(self):
        """Tell if the message is in the rejected state."""
        return self.moderation_status == STATUS_REJECTED
    def is_accepted(self):
        """Tell if the message is in the accepted state."""
        return self.moderation_status == STATUS_ACCEPTED

    @property
    def is_new(self):
        """Tell if the recipient has not yet read the message."""
        return self.read_at is None

    @property
    def is_replied(self):
        """Tell if the recipient has written a reply to the message."""
        return self.replied_at is not None
    
    @property
    def better_count(self):
        """ Expensive, but conversation-accurate message count for this thread. """
        if not self.thread_id:
            return 0
        return self._meta.model.objects.filter(thread_id=self.thread_id).count()

    def _obfuscated_email(self):
        """
        Return the email field as obfuscated, to keep it undisclosed.

        Format is:
            first 4 characters of the hash email + '..' + last 4 characters of the hash email + '@' + domain without TLD
        Example:
            foo@domain.com -> 1a2b..e8f9@domain

        """
        email = self.email
        data = email + settings.SECRET_KEY
        digest = hashlib.md5(data.encode()).hexdigest()  # encode(): py3 needs a buffer of bytes
        shrunken_digest = '..'.join((digest[:4], digest[-4:]))  # 32 characters is too long and is useless
        bits = email.split('@')
        if len(bits) != 2:
            return ''
        domain = bits[1]
        return '@'.join((shrunken_digest, domain.rsplit('.', 1)[0]))  # leave off the TLD to gain some space

    def admin_sender(self):
        """
        Return the sender either as a username or as a plain email.
        Designed for the Admin site.

        """
        if self.sender:
            return str(self.sender)
        else:
            return '<{0}>'.format(self.email)
    admin_sender.short_description = _("sender")
    admin_sender.admin_order_field = 'sender'

    # Give the sender either as a username or as a plain email.
    clear_sender = property(admin_sender)

    @property
    def obfuscated_sender(self):
        """Return the sender either as a username or as an undisclosed email."""
        if self.sender:
            return get_user_representation(self.sender)
        else:
            return self._obfuscated_email()

    def admin_recipient(self):
        """
        Return the recipient either as a username or as a plain email.
        Designed for the Admin site.

        """
        if self.recipient:
            return str(self.recipient)
        else:
            return '<{0}>'.format(self.email)
    admin_recipient.short_description = _("recipient")
    admin_recipient.admin_order_field = 'recipient'

    # Give the recipient either as a username or as a plain email.
    clear_recipient = property(admin_recipient)

    @property
    def obfuscated_recipient(self):
        """Return the recipient either as a username or as an undisclosed email."""
        if self.recipient:
            return get_user_representation(self.recipient)
        else:
            return self._obfuscated_email()

    def other_participants(self, user):
        """ For a given message and the current user, returns all other participants of this conversation,
        or a list with one element, the other person that isn't our user if the message is not part of a multi conversation """
        if not self.multi_conversation:
            return [self.sender if self.recipient == user else self.recipient]
        return [part for part in self.multi_conversation.participants.all() if not part == user]

    def get_replies_count(self):
        """Return the number of accepted responses."""
        return self.next_messages.filter(moderation_status=STATUS_ACCEPTED).count()

    def quote(self, format_subject, format_body=None):
        """Return a dictionary of quote values to initiate a reply."""
        values = {'subject': format_subject(self.subject)[:self.SUBJECT_MAX_LENGTH]}
        if format_body:
            values['body'] = format_body(self.obfuscated_sender, self.body)
        return values

    def clean(self):
        """Check some validity constraints."""
        if not (self.sender_id is not None or self.email):
            raise ValidationError(ugettext("Undefined sender."))

    def clean_moderation(self, initial_status, user=None):
        """Adjust automatically some fields, according to status workflow."""
        if self.moderation_status != initial_status:
            self.moderation_date = now()
            self.moderation_by = user
            if self.is_rejected():
                # even if maybe previously deleted during a temporary 'accepted' stay
                self.recipient_deleted_at = now()
            elif initial_status == STATUS_REJECTED:
                # rollback
                self.recipient_deleted_at = None

    def clean_for_visitor(self):
        """Do some auto-read and auto-delete, because there is no one to do it (no account)."""
        if self.sender_id is None:
            # no need to wait for a final moderation status to mark as deleted
            if not self.sender_deleted_at:
                self.sender_deleted_at = now()
        elif self.recipient_id is None:
            if self.is_accepted():
                if not self.read_at:
                    self.read_at = now()
                if not self.recipient_deleted_at:
                    self.recipient_deleted_at = now()
            else:
                # rollbacks
                if self.read_at:
                    self.read_at = None
                # but stay deleted if rejected
                if self.is_pending() and self.recipient_deleted_at:
                    self.recipient_deleted_at = None

    def update_parent(self, initial_status):
        """Update the parent to actualize its response state."""
        if self.moderation_status != initial_status:
            parent = self.parent
            if self.is_accepted():
                # keep the very first date; no need to do differently
                if parent and (not parent.replied_at or self.sent_at < parent.replied_at):
                    parent.replied_at = self.sent_at
                    parent.save()
            elif initial_status == STATUS_ACCEPTED:
                if parent and parent.replied_at == self.sent_at:
                    # rollback, but there may be some other valid replies
                    try:
                        other_date = parent.next_messages\
                            .exclude(pk=self.pk).filter(moderation_status=STATUS_ACCEPTED)\
                            .values_list('sent_at', flat=True)\
                            .order_by('sent_at')[:1].get()
                        parent.replied_at = other_date
                    except Message.DoesNotExist:
                        parent.replied_at = None
                    parent.save()

    def notify_users(self, initial_status, site, is_auto_moderated=True):
        """Notify the rejection (to sender) or the acceptance (to recipient) of the message."""
        if initial_status == STATUS_PENDING:
            if self.is_rejected():
                # Bypass: for an online user, no need to notify when rejection is immediate.
                # Only useful for a visitor as an archive copy of the message, otherwise lost.
                if not (self.sender_id is not None and is_auto_moderated):
                    (notify_user if self.sender_id is not None else email_visitor)(self, 'rejection', site)
            elif self.is_accepted():
                (notify_user if self.recipient_id is not None else email_visitor)(self, 'acceptance', site)

    def get_dates(self):
        """Get some dates to restore later."""
        return (self.sender_deleted_at, self.recipient_deleted_at, self.read_at)

    def set_dates(self, sender_deleted_at, recipient_deleted_at, read_at):
        """Restore some dates."""
        self.sender_deleted_at = sender_deleted_at
        self.recipient_deleted_at = recipient_deleted_at
        self.read_at = read_at

    def get_moderation(self):
        """Get moderation information to restore later."""
        return (self.moderation_status, self.moderation_by_id, self.moderation_date, self.moderation_reason)

    def set_moderation(self, status, by_id, date, reason):
        """Restore moderation information."""
        self.moderation_status = status
        self.moderation_by_id = by_id
        self.moderation_date = date
        self.moderation_reason = reason

    def auto_moderate(self, moderators):
        """Run a chain of auto-moderators."""
        auto = None
        final_reason = ''
        percents = []
        reasons = []
        if not isinstance(moderators, (list, tuple)):
            moderators = (moderators,)
        for moderator in moderators:
            rating = moderator(self)
            if rating is None: continue
            if isinstance(rating, tuple):
                percent, reason = rating
            else:
                percent = rating
                reason = getattr(moderator, 'default_reason', '')
            if percent is False: percent = 0
            if percent is True: percent = 100
            if not 0 <= percent <= 100: continue
            if percent == 0:
                auto = False
                final_reason = reason
                break
            elif percent == 100:
                auto = True
                break
            percents.append(percent)
            reasons.append(reason)
        if auto is None and percents:
            average = float(sum(percents)) / len(percents)
            final_reason = ', '.join([r for i, r in enumerate(reasons) if r and not r.isspace() and percents[i] < 50])
            auto = average >= 50
        if auto is None:
            auto = getattr(settings, 'POSTMAN_AUTO_MODERATE_AS', None)
        if auto is True:
            self.moderation_status = STATUS_ACCEPTED
        elif auto is False:
            self.moderation_status = STATUS_REJECTED
            self.moderation_reason = final_reason


class PendingMessageManager(models.Manager):
    """The manager for PendingMessage."""

    def get_query_set(self):  # for Django <= 1.5
        return super(PendingMessageManager, self).get_query_set().filter(moderation_status=STATUS_PENDING)

    def get_queryset(self):  # changed in Django 1.6: "The get_queryset method was previously named get_query_set."
        """Filter to get only pending objects."""
        return super(PendingMessageManager, self).get_queryset().filter(moderation_status=STATUS_PENDING)


class PendingMessage(Message):
    """
    A proxy to Message, focused on pending objects to accept or reject.
    """

    objects = PendingMessageManager()

    class Meta(object):
        verbose_name = _("pending message")
        verbose_name_plural = _("pending messages")
        proxy = True

    def set_accepted(self):
        """Set the message as accepted."""
        self.moderation_status = STATUS_ACCEPTED

    def set_rejected(self):
        """Set the message as rejected."""
        self.moderation_status = STATUS_REJECTED
