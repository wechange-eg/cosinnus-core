from __future__ import unicode_literals

from builtins import object

from six.moves.urllib.parse import urlsplit, urlunsplit

from django import VERSION
from cosinnus.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cosinnus.views.attached_object import AttachableViewMixin
from cosinnus.utils.permissions import check_user_superuser,\
    check_user_can_see_user
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import ugettext as _, ugettext_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView, TemplateView, View

from . import OPTION_MESSAGES
from .fields import autocompleter_app
from .forms import WriteForm, AnonymousWriteForm, QuickReplyForm, FullReplyForm
from .models import Message, get_order_by
from .utils import format_subject, format_body
from django.http.response import HttpResponseForbidden

login_required_m = method_decorator(login_required)
csrf_protect_m = method_decorator(csrf_protect)


##########
# Helpers
##########
def _get_referer(request):
    """Return the HTTP_REFERER, if existing."""
    if 'HTTP_REFERER' in request.META:
        sr = urlsplit(request.META['HTTP_REFERER'])
        return urlunsplit(('', '', sr.path, sr.query, sr.fragment))


########
# Views
########
class NamespaceMixin(object):
    """Common code to manage the namespace."""

    def render_to_response(self, context, **response_kwargs):
        if VERSION >= (1, 8):
            self.request.current_app = self.request.resolver_match.namespace
        else:
            response_kwargs['current_app'] = self.request.resolver_match.namespace
        return super(NamespaceMixin, self).render_to_response(context, **response_kwargs)


class FolderMixin(NamespaceMixin, object):
    """Code common to the folders."""
    http_method_names = ['get']

    @login_required_m
    def dispatch(self, *args, **kwargs):
        return super(FolderMixin, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(FolderMixin, self).get_context_data(**kwargs)
        params = {}
        option = kwargs.get('option')
        if option:
            params['option'] = option
        order_by = get_order_by(self.request.GET)
        if order_by:
            params['order_by'] = order_by
        msgs = getattr(Message.objects, self.folder_name)(self.request.user, **params)
        viewname = 'postman:' + self.view_name
        current_instance = self.request.resolver_match.namespace
        context.update({
            'pm_messages': msgs,  # avoid 'messages', already used by contrib.messages
            'by_conversation': option is None,
            'by_message': option == OPTION_MESSAGES,
            'by_conversation_url': reverse(viewname, current_app=current_instance),
            'by_message_url': reverse(viewname, args=[OPTION_MESSAGES], current_app=current_instance),
            'current_url': self.request.get_full_path(),
            'gets': self.request.GET,  # useful to postman_order_by template tag
        })
        return context


class InboxView(FolderMixin, TemplateView):
    """
    Display the list of received messages for the current user.

    Optional URLconf name-based argument:
        ``option``: display option:
            OPTION_MESSAGES to view all messages
            default to None to view only the last message for each conversation
    Optional URLconf configuration attribute:
        ``template_name``: the name of the template to use

    """
    # for FolderMixin:
    folder_name = 'inbox'
    view_name = 'inbox'
    # for TemplateView:
    template_name = 'postman/inbox.html'


class SentView(FolderMixin, TemplateView):
    """
    Display the list of sent messages for the current user.

    Optional arguments and attributes: refer to InboxView.

    """
    # for FolderMixin:
    folder_name = 'sent'
    view_name = 'sent'
    # for TemplateView:
    template_name = 'postman/sent.html'


class ArchivesView(FolderMixin, TemplateView):
    """
    Display the list of archived messages for the current user.

    Optional arguments and attributes: refer to InboxView.

    """
    # for FolderMixin:
    folder_name = 'archives'
    view_name = 'archives'
    # for TemplateView:
    template_name = 'postman/archives.html'


class TrashView(FolderMixin, TemplateView):
    """
    Display the list of deleted messages for the current user.

    Optional arguments and attributes: refer to InboxView.

    """
    # for FolderMixin:
    folder_name = 'trash'
    view_name = 'trash'
    # for TemplateView:
    template_name = 'postman/trash.html'


class RestrictRecipientMixin(object):
    
    def check_restricted_recipient(self, message, user=None):
        if message.multi_conversation:
            recipient_group_slugs = message.multi_conversation.targetted_groups.all().values_list('slug', flat=True)
            if getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None) and getattr(settings, 'NEWW_FORUM_GROUP_SLUG') in recipient_group_slugs and not check_user_superuser(user or self.request.user):
                return True
        return False
    

class ComposeMixin(AttachableViewMixin, NamespaceMixin, object):
    """
    Code common to the write and reply views.

    Optional attributes:
        ``success_url``: where to redirect to after a successful POST
        ``user_filter``: a filter for recipients
        ``exchange_filter``: a filter for exchanges between a sender and a recipient
        ``max``: an upper limit for the recipients number
        ``auto_moderators``: a list of auto-moderation functions

    """
    http_method_names = ['get', 'post']
    success_url = None
    user_filter = None
    exchange_filter = None
    max = None
    auto_moderators = []

    def get_form_kwargs(self):
        kwargs = super(ComposeMixin, self).get_form_kwargs()
        if self.request.method == 'POST':
            kwargs.update({
                'sender': self.request.user,
                'user_filter': self.user_filter,
                'exchange_filter': self.exchange_filter,
                'max': self.max,
                'site': get_current_site(self.request),
            })
        return kwargs

    def get_success_url(self):
        return self.request.GET.get('next') or self.success_url or _get_referer(self.request) or 'postman:inbox'

    def form_valid(self, form):
        params = {'auto_moderators': self.auto_moderators}
        if hasattr(self, 'parent'):  # only in the ReplyView case
            params['parent'] = self.parent
        is_successful = form.save(**params)
        super(ComposeMixin, self).form_valid(form)
        
        # if we have uploaded any attachments, then those are set to private
        # we tag the recipient in that file so they can see it (or recipients if the form copied many)
        all_recipients = [form.instance.recipient]
        all_recipients.extend([msg.recipient for msg in getattr(form, 'extra_instances', [])])
        all_recipients = list(set(all_recipients))
        for attached_object in form.instance.attached_objects.all():
            for recipient in all_recipients:
                attached_object.target_object.media_tag.persons.add(recipient)
        
        if is_successful:
            messages.success(self.request, _("Message successfully sent."), fail_silently=True)
        else:
            messages.warning(self.request, _("Message rejected for at least one recipient."), fail_silently=True)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(ComposeMixin, self).get_context_data(**kwargs)
        context.update({
            'autocompleter_app': autocompleter_app,
            'next_url': self.request.GET.get('next') or _get_referer(self.request),
        })
        return context


class WriteView(ComposeMixin, FormView):
    """
    Display a form to compose a message.

    Optional URLconf name-based argument:
        ``recipients``: a colon-separated list of usernames
    Optional attributes:
        ``form_classes``: a 2-tuple of form classes
        ``autocomplete_channels``: a channel name or a 2-tuple of names
        ``template_name``: the name of the template to use
        + those of ComposeMixin

    """
    form_classes = (WriteForm, AnonymousWriteForm)
    autocomplete_channels = None
    template_name = 'postman/write.html'

    @csrf_protect_m
    def dispatch(self, *args, **kwargs):
        # view is disabled in archive mode
        if getattr(settings, 'COSINNUS_POSTMAN_ARCHIVE_MODE', False):
            return HttpResponseForbidden('This view is disabled.')
        
        if getattr(settings, 'POSTMAN_DISALLOW_ANONYMOUS', False):
            return login_required(super(WriteView, self).dispatch)(*args, **kwargs)
        return super(WriteView, self).dispatch(*args, **kwargs)

    def get_form_class(self):
        return self.form_classes[0] if self.request.user.is_authenticated else self.form_classes[1]

    def get_initial(self):
        initial = super(WriteView, self).get_initial()
        if self.request.method == 'GET':
            initial.update(list(self.request.GET.items()))  # allow optional initializations by query string
            
            recipients = []
            user_recipients = self.kwargs.get('recipients')
            if user_recipients:
                # order_by() is not mandatory, but: a) it doesn't hurt; b) it eases the test suite
                # and anyway the original ordering cannot be respected.
                user_model = get_user_model()
                name_user_as = getattr(settings, 'POSTMAN_NAME_USER_AS', user_model.USERNAME_FIELD)
                users = user_model.objects.filter(
                    is_active=True,
                    **{'{0}__in'.format(name_user_as): [r.strip() for r in user_recipients.split(',') if r and not r.isspace()]}
                ).order_by(name_user_as)
                usernames = ['user:%s' % getattr(user, name_user_as) for user in users if check_user_can_see_user(self.request.user, user) and not user.id == self.request.user.id]
                if usernames:
                    recipients.extend(usernames)
            group_recipients = self.kwargs.get('group_recipients')
            if group_recipients:
                groups = ['group:%s' % group_slug for group_slug in group_recipients.split(',')]
                if groups:
                    recipients.extend(groups)
            
            initial['recipients'] = ', '.join(recipients)
            
        return initial

    def get_form_kwargs(self):
        kwargs = super(WriteView, self).get_form_kwargs()
        if isinstance(self.autocomplete_channels, tuple) and len(self.autocomplete_channels) == 2:
            channel = self.autocomplete_channels[self.request.user.is_anonymous]
        else:
            channel = self.autocomplete_channels
        kwargs['channel'] = channel
        return kwargs


class ReplyView(ComposeMixin, RestrictRecipientMixin, FormView):
    """
    Display a form to compose a reply.

    Optional attributes:
        ``form_class``: the form class to use
        ``formatters``: a 2-tuple of functions to prefill the subject and body fields
        ``autocomplete_channel``: a channel name
        ``template_name``: the name of the template to use
        + those of ComposeMixin

    """
    form_class = FullReplyForm
    formatters = (format_subject, format_body)
    autocomplete_channel = None
    template_name = 'postman/reply.html'

    @csrf_protect_m
    @login_required_m
    def dispatch(self, request, message_id, *args, **kwargs):
        # view is disabled in archive mode
        if getattr(settings, 'COSINNUS_POSTMAN_ARCHIVE_MODE', False):
            return HttpResponseForbidden('This view is disabled.')
        
        perms = Message.objects.perms(request.user)
        self.parent = get_object_or_404(Message, perms, pk=message_id)
        return super(ReplyView, self).dispatch(request,*args, **kwargs)

    def get_initial(self):
        self.initial = self.parent.quote(*self.formatters)  # will also be partially used in get_form_kwargs()
        if self.request.method == 'GET':
            self.initial.update(list(self.request.GET.items()))  # allow overwriting of the defaults by query string
        return self.initial

    def get_form_kwargs(self):
        kwargs = super(ReplyView, self).get_form_kwargs()
        kwargs['channel'] = self.autocomplete_channel
        if self.request.method == 'POST':
            if 'subject' not in kwargs['data']:  # case of the quick reply form
                post = kwargs['data'].copy()  # self.request.POST is immutable
                post['subject'] = self.initial['subject']
                kwargs['data'] = post
            kwargs['recipient'] = self.parent.sender or self.parent.email
            if self.parent.multi_conversation:
                # limit answering to forum:
                if self.check_restricted_recipient(self.parent):
                    raise PermissionDenied(_('Only Administrators may send a message to this project/group!'))
                
                post = kwargs['data'].copy()  # self.request.POST is immutable
                post.setlist('recipients', ['user:%d' % rec.id for rec in self.parent.multi_conversation.participants.all()])
                kwargs['data'] = post
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(ReplyView, self).get_context_data(**kwargs)
        context['recipient'] = self.parent.obfuscated_sender
        return context


class DisplayMixin(NamespaceMixin, RestrictRecipientMixin, object):
    """
    Code common to the by-message and by-conversation views.

    Optional attributes:
        ``form_class``: the form class to use
        ``formatters``: a 2-tuple of functions to prefill the subject and body fields
        ``template_name``: the name of the template to use

    """
    http_method_names = ['get']
    form_class = QuickReplyForm
    formatters = (format_subject, format_body if getattr(settings, 'POSTMAN_QUICKREPLY_QUOTE_BODY', False) else None)
    template_name = 'postman/view.html'

    @login_required_m
    def dispatch(self, *args, **kwargs):
        return super(DisplayMixin, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        user = request.user
        self.msgs = Message.objects.thread(user, self.filter)
        if not self.msgs:
            raise Http404
        Message.objects.set_read(user, self.filter)
        # Mark root message as LastVisited
        self.msgs[0].mark_visited(user)
        return super(DisplayMixin, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DisplayMixin, self).get_context_data(**kwargs)
        user = self.request.user
        # are all messages archived ?
        for m in self.msgs:
            if not getattr(m, ('sender' if m.sender == user else 'recipient') + '_archived'):
                archived = False
                break
        else:
            archived = True
        # look for the most recent received message (and non-deleted to comply with the future perms() control), if any
        for m in reversed(self.msgs):
            if m.recipient == user and not m.recipient_deleted_at:
                received = m
                break
        else:
            received = None
            
        context.update({
            'pm_messages': self.msgs,
            'archived': archived,
            'reply_to_pk': received.pk if received else None,
            'form': self.form_class(initial=received.quote(*self.formatters)) if received else None,
            'next_url': self.request.GET.get('next') or reverse('postman:inbox', current_app=self.request.resolver_match.namespace),
            'disable_reply_all': self.check_restricted_recipient(self.msgs[0]),
        })
        return context


class MessageView(DisplayMixin, TemplateView):
    """Display one specific message."""

    def get(self, request, message_id, *args, **kwargs):
        self.filter = Q(pk=message_id)
        return super(MessageView, self).get(request, *args, **kwargs)


class ConversationView(DisplayMixin, TemplateView):
    """Display a conversation."""

    def get(self, request, thread_id, *args, **kwargs):
        self.filter = Q(thread=thread_id)
        return super(ConversationView, self).get(request, *args, **kwargs)


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
    success_url = None

    @csrf_protect_m
    @login_required_m
    def dispatch(self, *args, **kwargs):
        return super(UpdateMessageMixin, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        next_url = _get_referer(request) or 'postman:inbox'
        pks = request.POST.getlist('pks')
        tpks = request.POST.getlist('tpks')
        if pks or tpks:
            user = request.user
            filter = Q(pk__in=pks) | Q(thread__in=tpks)
            recipient_rows = Message.objects.as_recipient(user, filter).update(**{'recipient_{0}'.format(self.field_bit): self.field_value})
            sender_rows = Message.objects.as_sender(user, filter).update(**{'sender_{0}'.format(self.field_bit): self.field_value})
            if not (recipient_rows or sender_rows):
                raise Http404  # abnormal enough, like forged ids
            messages.success(request, self.success_msg, fail_silently=True)
            return redirect(request.GET.get('next') or self.success_url or next_url)
        else:
            messages.warning(request, _("Select at least one object."), fail_silently=True)
            return redirect(next_url)


class ArchiveView(UpdateMessageMixin, View):
    """Mark messages/conversations as archived."""
    field_bit = 'archived'
    success_msg = ugettext_lazy("Messages or conversations successfully archived.")
    field_value = True


class DeleteView(UpdateMessageMixin, View):
    """Mark messages/conversations as deleted."""
    field_bit = 'deleted_at'
    success_msg = ugettext_lazy("Messages or conversations successfully deleted.")
    field_value = now()


class UndeleteView(UpdateMessageMixin, View):
    """Revert messages/conversations from marked as deleted."""
    field_bit = 'deleted_at'
    success_msg = ugettext_lazy("Messages or conversations successfully recovered.")
