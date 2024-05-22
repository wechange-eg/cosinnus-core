"""
If the default usage of the views suits you, simply use a line like
this one in your root URLconf to set up the default URLs::

    (r'^messages/', include('postman.urls')),

Otherwise you may customize the behavior by passing extra parameters.

Recipients Max
--------------
Views supporting the parameter are: ``WriteView``, ``ReplyView``.
Example::
    ...View.as_view(max=3), name='postman_write'),
See also the ``POSTMAN_DISALLOW_MULTIRECIPIENTS`` setting

User filter
-----------
Views supporting a user filter are: ``WriteView``, ``ReplyView``.
Example::
    def my_user_filter(user):
        if user.get_profile().is_absent:
            return "is away"
        return None
    ...
    ...View.as_view(user_filter=my_user_filter), name='postman_write'),

function interface:
In: a User instance
Out: None, False, '', 'a reason', or ValidationError

Exchange filter
---------------
Views supporting an exchange filter are: ``WriteView``, ``ReplyView``.
Example::
    def my_exchange_filter(sender, recipient, recipients_list):
        if recipient.relationships.exists(sender, RelationshipStatus.objects.blocking()):
            return "has blacklisted you"
        return None
    ...
    ...View.as_view(exchange_filter=my_exchange_filter), name='postman_write'),

function interface:
In:
    ``sender``: a User instance
    ``recipient``: a User instance
    ``recipients_list``: the full list of recipients
Out: None, False, '', 'a reason', or ValidationError

Auto-complete field
-------------------
Views supporting an auto-complete parameter are: ``WriteView``, ``ReplyView``.
Examples::
    ...View.as_view(autocomplete_channels=(None,'anonymous_ac')), name='postman_write'),
    ...View.as_view(autocomplete_channels='write_ac'), name='postman_write'),
    ...View.as_view(autocomplete_channel='reply_ac'), name='postman_reply'),

Auto moderators
---------------
Views supporting an ``auto-moderators`` parameter are: ``WriteView``, ``ReplyView``.
Example::
    def mod1(message):
        # ...
        return None
    def mod2(message):
        # ...
        return None
    mod2.default_reason = 'mod2 default reason'
    ...
    ...View.as_view(auto_moderators=(mod1, mod2)), name='postman_write'),
    ...View.as_view(auto_moderators=mod1), name='postman_reply'),

function interface:
In: ``message``: a Message instance
Out: rating or (rating, "reason")
    with reting: None, 0 or False, 100 or True, 1..99

Others
------
Refer to documentation.
    ...View.as_view(form_classes=(MyCustomWriteForm, MyCustomAnonymousWriteForm)), name='postman_write'),
    ...View.as_view(form_class=MyCustomFullReplyForm), name='postman_reply'),
    ...View.as_view(form_class=MyCustomQuickReplyForm), name='postman_view'),
    ...View.as_view(template_name='my_custom_view.html'), name='postman_view'),
    ...View.as_view(success_url='postman_inbox'), name='postman_reply'),
    ...View.as_view(formatters=(format_subject, format_body)), name='postman_reply'),
    ...View.as_view(formatters=(format_subject, format_body)), name='postman_view'),

"""

from __future__ import unicode_literals

from django.urls import path, re_path
from django.views.generic.base import RedirectView

from cosinnus.views.user import UserSelect2View
from cosinnus_message.forms import CustomReplyForm, CustomWriteForm
from cosinnus_message.views import (
    ArchiveView,
    CosinnusConversationView,
    CosinnusMessageView,
    DeleteView,
    MarkAsReadView,
    UndeleteView,
)
from postman import OPTIONS
from postman.views import ArchivesView, InboxView, ReplyView, SentView, TrashView, WriteView

urlpatterns = [
    path('', RedirectView.as_view(url='posteingang/', permanent=False), name='index'),
    path('ajax/userselect/', UserSelect2View.as_view(), name='user_select2_view'),
    path('nachricht/<int:message_id>/', CosinnusMessageView.as_view(), name='view'),
    path('nachricht/t/<int:thread_id>/', CosinnusConversationView.as_view(), name='view_conversation'),
    path('archiv/', ArchiveView.as_view(), name='archive'),
    path('loeschen/', DeleteView.as_view(), name='delete'),
    path('wiederherstellen/', UndeleteView.as_view(), name='undelete'),
    path('gelesen/', MarkAsReadView.as_view(), name='markasread'),
    re_path(r'^posteingang/(?:(?P<option>' + OPTIONS + ')/)?$', InboxView.as_view(), name='inbox'),
    re_path(r'^gesendet/(?:(?P<option>' + OPTIONS + ')/)?$', SentView.as_view(), name='sent'),
    re_path(r'^archives/(?:(?P<option>' + OPTIONS + ')/)?$', ArchivesView.as_view(), name='archives'),
    re_path(r'^papierkorb/(?:(?P<option>' + OPTIONS + ')/)?$', TrashView.as_view(), name='trash'),
    path('antworten/<int:message_id>/', ReplyView.as_view(form_class=CustomReplyForm), name='reply'),
    re_path(
        r'neu/(?:(?P<recipients>[^/]+)/)?',
        WriteView.as_view(form_classes=(CustomWriteForm, CustomWriteForm)),
        name='write',
    ),
    re_path(
        r'g/neu/(?:(?P<group_recipients>[^/]+)/)?',
        WriteView.as_view(form_classes=(CustomWriteForm, CustomWriteForm)),
        name='write-group',
    ),
]
