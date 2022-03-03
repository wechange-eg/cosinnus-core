"""
You may define your own custom forms, based or inspired by the following ones.

Examples of customization:
    recipients = CommaSeparatedUserField(label=("Recipients", "Recipient"),
        min=2,
        max=5,
        user_filter=my_user_filter,
        channel='my_channel',
    )
    can_overwrite_limits = False
    exchange_filter = staticmethod(my_exchange_filter)

"""
from __future__ import unicode_literals

from builtins import str
from builtins import object
from django import forms
from django.conf import settings
from cosinnus.forms.attached_object import FormAttachableMixin
from copy import copy, deepcopy
from postman.models import MultiConversation
from annoying.functions import get_object_or_None
try:
    from django.contrib.auth import get_user_model  # Django 1.5
except ImportError:
    from postman.future_1_5 import get_user_model
from django.db import transaction
from django.utils.translation import ugettext, ugettext_lazy as _

from .fields import CommaSeparatedUserField
from .models import Message, get_user_name
from .utils import WRAP_WIDTH


class BaseWriteForm(FormAttachableMixin, forms.ModelForm):
    """The base class for other forms."""
    class Meta(object):
        model = Message
        fields = ('body',)
        widgets = {
            # for better confort, ensure a 'cols' of at least
            # the 'width' of the body quote formatter.
            'body': forms.Textarea(attrs={'cols': WRAP_WIDTH, 'rows': 12}),
        }

    error_css_class = 'error'
    required_css_class = 'required'
    # any 'saved-away' instances for extra recipients that are just copied out
    # by setting pk=None are stored here
    extra_instances = []
    
    # can be set on init to prevent any notifications going out
    do_not_notify_users = False

    def __init__(self, *args, **kwargs):
        sender = kwargs.pop('sender', None)
        exchange_filter = kwargs.pop('exchange_filter', None)
        user_filter = kwargs.pop('user_filter', None)
        max = kwargs.pop('max', None)
        channel = kwargs.pop('channel', None)
        self.site = kwargs.pop('site', None)
        self.do_not_notify_users = kwargs.pop('do_not_notify_users', self.do_not_notify_users)
        super(BaseWriteForm, self).__init__(*args, **kwargs)

        self.instance.sender = sender if (sender and sender.is_authenticated) else None
        if exchange_filter:
            self.exchange_filter = exchange_filter
        if 'recipients' in self.fields:
            if user_filter and hasattr(self.fields['recipients'], 'user_filter'):
                self.fields['recipients'].user_filter = user_filter

            if getattr(settings, 'POSTMAN_DISALLOW_MULTIRECIPIENTS', False):
                max = 1
            if max is not None and hasattr(self.fields['recipients'], 'set_max') \
            and getattr(self, 'can_overwrite_limits', True):
                self.fields['recipients'].set_max(max)

            if channel and hasattr(self.fields['recipients'], 'set_arg'):
                self.fields['recipients'].set_arg(channel)

    error_messages = {
        'filtered': _("Writing to some users is not possible: {users}."),
        'filtered_user': _("{username}"),
        'filtered_user_with_reason': _("{username} ({reason})"),
    }
    def clean_recipients(self):
        """Check no filter prohibits the exchange."""
        recipients = self.cleaned_data['recipients']
        exchange_filter = getattr(self, 'exchange_filter', None)
        if exchange_filter:
            errors = []
            filtered_names = []
            recipients_list = recipients[:]
            for u in recipients_list:
                try:
                    reason = exchange_filter(self.instance.sender, u, recipients_list)
                    if reason is not None:
                        recipients.remove(u)
                        filtered_names.append(
                            self.error_messages[
                                'filtered_user_with_reason' if reason else 'filtered_user'
                            ].format(username=get_user_name(u), reason=reason)
                        )
                except forms.ValidationError as e:
                    recipients.remove(u)
                    errors.extend(e.messages)
            if filtered_names:
                errors.append(self.error_messages['filtered'].format(users=', '.join(filtered_names)))
            if errors:
                raise forms.ValidationError(errors)
        return recipients

    def save(self, recipient=None, parent=None, auto_moderators=[]):
        """
        Save as many messages as there are recipients.

        Additional actions:
        - If it's a reply, build a conversation
        - Call auto-moderators
        - Notify parties if needed

        Return False if one of the messages is rejected.

        """
        sender = self.instance.sender
        recipients = self.cleaned_data.get('recipients', [])
        
        if recipient:
            if isinstance(recipient, get_user_model()) and recipient in recipients:
                recipients.remove(recipient)
            recipients.insert(0, recipient)
        recipients = list(set(recipients))
        recipients = [_rec for _rec in recipients if not _rec == sender]
        is_successful = True

        
        is_multi_conversation = len(recipients) > 1 and all([isinstance(rec, get_user_model()) for rec in recipients])
        do_reply_single_copy = parent and self.data.get('reply_all') == '0' and is_multi_conversation
        
        if do_reply_single_copy:
            # if in a conversation, we want to reply only to the root sender, we copy the root message
            new_root_message = parent if not parent.thread_id else parent.thread
            new_root_message = deepcopy(new_root_message)
            new_root_message.pk = None
            new_root_message.thread = None
            new_root_message.thread_id = None
            new_root_message.multi_conversation = None
            new_root_message.multi_conversation_id = None
            new_root_message.level = 0
            new_root_message.sender_archived = False
            new_root_message.recipient_archived = False
            new_root_message.sender_deleted_at = None
            new_root_message.recipient_deleted_at = None
            new_root_message.recipient = sender
            new_root_message.save()
            recipient = new_root_message.sender
            recipients = [recipient]
            parent = new_root_message
        
        
        multiconv = None
        level = 0
        is_master = True
        if is_multi_conversation and not do_reply_single_copy:
            # is this a first message in a conversation or a reply?
            if parent:
                level = parent.level + 1 
                multiconv = parent.multi_conversation
            else:
                level = 0
                multiconv = MultiConversation.objects.create()
                multiconv.participants.add(sender, *recipients)
                # if the user sent a message to one or more groups, save them in the conversation
                targetted_groups = getattr(self, 'targetted_groups', [])
                if targetted_groups:
                    multiconv.targetted_groups.add(*targetted_groups)
        
        original_parent = parent
        
        # important to clear because forms are reused
        self.extra_instances = []
        for r in recipients:
            # in a multiconversation reply, find the actual parent for this recipient's message object of the conversation
            # (each recipient has their own thread, connected my a MultiConversation)
            if multiconv and original_parent and not do_reply_single_copy:
                # the parent is unambiguous, it is the message in the conversation's last level where either
                # A) the recipient is the same (when this message goes to any participant but the last sender)
                parent = get_object_or_None(Message, multi_conversation=multiconv, level=0, recipient=r)
                if not parent:
                    # B) or the message where the recipient was the current sender (when this message goes to the last sender)
                    # we choose this one, because the last sender is sender of all messages on that level
                    parent = get_object_or_None(Message, multi_conversation=multiconv, level=0, sender=r, recipient=sender)
                if not parent:
                    # todo: catch better
                    raise Exception('Programming Error: No parent found for %s' % str({'sender': sender, 'recipient': r, 'multiconv': multiconv}))
            
            if parent and not parent.thread_id:  # at the very first reply, make it a conversation
                parent.thread = parent
                parent.save()
                # but delay the setting of parent.replied_at to the moderation step
            if parent:
                self.instance.parent = parent
                self.instance.thread_id = parent.thread_id
                
            initial_moderation = self.instance.get_moderation()
            initial_dates = self.instance.get_dates()
            initial_status = self.instance.moderation_status
                
            if isinstance(r, get_user_model()):
                self.instance.recipient = r
            else:
                self.instance.recipient = None
                self.instance.email = r
                
            self.instance.pk = None  # force_insert=True is not accessible from here
            self.instance.auto_moderate(auto_moderators)
            self.instance.clean_moderation(initial_status)
            self.instance.clean_for_visitor()
            
            # set multi conversation. only the first message in this level is the master (used for disambiguating on
            # which message to ask for sender_deleted_at etc)
            if multiconv and not do_reply_single_copy:
                self.instance.multi_conversation = multiconv
                self.instance.level = level
                
                if self.instance.thread_id:
                    # in a multiconversation, for all messages but the first, the master_for_sender flag must be
                    # on the message object that is being sent to the person that was sender of the first (thread) message object
                    thread = Message.objects.get(id=self.instance.thread_id) # need to refetch, since we only change the thread_id, the fk object is stale
                    self.instance.master_for_sender = (r == thread.sender)
                else:
                    # otherwise, the first message will be master
                    self.instance.master_for_sender = is_master
                    is_master = False
            
            m = super(BaseWriteForm, self).save()
                        
            # save away a copied message to another recipient so we can access them all later (for adding attachable objects)
            self.extra_instances.append(copy(self.instance))

            if self.instance.is_rejected():
                is_successful = False
            self.instance.update_parent(initial_status)
            if not self.do_not_notify_users:
                self.instance.notify_users(initial_status, self.site)
                
            # some resets for next reuse
            if not isinstance(r, get_user_model()):
                self.instance.email = ''
            self.instance.set_moderation(*initial_moderation)
            self.instance.set_dates(*initial_dates)
        
        return is_successful
    # commit_on_success() is deprecated in Django 1.6 and will be removed in Django 1.8
    save = transaction.atomic(save) if hasattr(transaction, 'atomic') else transaction.commit_on_success(save)


class WriteForm(BaseWriteForm):
    """The form for an authenticated user, to compose a message."""
    # specify help_text only to avoid the possible default 'Enter text to search.' of ajax_select v1.2.5
    recipients = CommaSeparatedUserField(label=(_("Recipients"), _("Recipient")), help_text='')

    class Meta(BaseWriteForm.Meta):
        fields = ('recipients', 'subject', 'body')


class AnonymousWriteForm(BaseWriteForm):
    """The form for an anonymous user, to compose a message."""
    # The 'max' customization should not be permitted here.
    # The features available to anonymous users should be kept to the strict minimum.
    can_overwrite_limits = False

    email = forms.EmailField(label=_("Email"))
    recipients = CommaSeparatedUserField(label=(_("Recipients"), _("Recipient")), help_text='', max=1)  # one recipient is enough

    class Meta(BaseWriteForm.Meta):
        fields = ('email', 'recipients', 'subject', 'body')


class BaseReplyForm(BaseWriteForm):
    """The base class for a reply to a message."""
    def __init__(self, *args, **kwargs):
        recipient = kwargs.pop('recipient', None)
        super(BaseReplyForm, self).__init__(*args, **kwargs)
        self.recipient = recipient

    def clean(self):
        """Check that the recipient is correctly initialized and no filter prohibits the exchange."""
        if not self.recipient:
            raise forms.ValidationError(ugettext("Undefined recipient."))

        exchange_filter = getattr(self, 'exchange_filter', None)
        if exchange_filter and isinstance(self.recipient, get_user_model()):
            try:
                reason = exchange_filter(self.instance.sender, self.recipient, None)
                if reason is not None:
                    raise forms.ValidationError(self.error_messages['filtered'].format(
                        users=self.error_messages[
                            'filtered_user_with_reason' if reason else 'filtered_user'
                        ].format(username=get_user_name(self.recipient), reason=reason)
                    ))
            except forms.ValidationError as e:
                raise forms.ValidationError(e.messages)
        return super(BaseReplyForm, self).clean()

    def save(self, *args, **kwargs):
        return super(BaseReplyForm, self).save(self.recipient, *args, **kwargs)


class QuickReplyForm(BaseReplyForm):
    """
    The form to use in the view of a message or a conversation, for a quick reply.

    The recipient is imposed and a default value for the subject will be provided.

    """
    pass


allow_copies = not getattr(settings, 'POSTMAN_DISALLOW_COPIES_ON_REPLY', False)
class FullReplyForm(BaseReplyForm):
    """The complete reply form."""
    if allow_copies:
        recipients = CommaSeparatedUserField(
            label=(_("Additional recipients"), _("Additional recipient")), help_text='', required=False)

    class Meta(BaseReplyForm.Meta):
        fields = (['recipients'] if allow_copies else []) + ['subject', 'body']
