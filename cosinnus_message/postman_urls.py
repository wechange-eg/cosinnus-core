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
from cosinnus_message.forms import CustomReplyForm, CustomWriteForm
from cosinnus_message.views import CosinnusMessageView,\
    CosinnusConversationView, ArchiveView, DeleteView, UndeleteView,\
    MarkAsReadView

from django.conf.urls import url
from django.views.generic.base import RedirectView

from postman import OPTIONS
from postman.views import (InboxView, SentView, ArchivesView, TrashView,
        WriteView, ReplyView)
from cosinnus.views.user import UserSelect2View


urlpatterns = [
    url(r'^$', RedirectView.as_view(url='posteingang/', permanent=False), name='index'),
    url(r'^ajax/userselect/$', UserSelect2View.as_view(), name='user_select2_view'),

    url(r'^nachricht/(?P<message_id>[\d]+)/$', CosinnusMessageView.as_view(), name='view'),
    url(r'^nachricht/t/(?P<thread_id>[\d]+)/$', CosinnusConversationView.as_view(), name='view_conversation'),
    url(r'^archiv/$', ArchiveView.as_view(), name='archive'),
    url(r'^loeschen/$', DeleteView.as_view(), name='delete'),
    url(r'^wiederherstellen/$', UndeleteView.as_view(), name='undelete'),
    url(r'^gelesen/$', MarkAsReadView.as_view(), name='markasread'),

    url(r'^posteingang/(?:(?P<option>'+OPTIONS+')/)?$', InboxView.as_view(), name='inbox'),
    url(r'^gesendet/(?:(?P<option>'+OPTIONS+')/)?$', SentView.as_view(), name='sent'),
    url(r'^archives/(?:(?P<option>'+OPTIONS+')/)?$', ArchivesView.as_view(), name='archives'),
    url(r'^papierkorb/(?:(?P<option>'+OPTIONS+')/)?$', TrashView.as_view(), name='trash'),
    url(r'^antworten/(?P<message_id>[\d:]+)/$', ReplyView.as_view(form_class=CustomReplyForm), name='reply'),
    url(r'^neu/(?:(?P<recipients>[^/]+)/)?$', WriteView.as_view(form_classes=(CustomWriteForm, CustomWriteForm)), name='write'),
    url(r'^g/neu/(?:(?P<group_recipients>[^/]+)/)?$', WriteView.as_view(form_classes=(CustomWriteForm, CustomWriteForm)), name='write-group'),
]
