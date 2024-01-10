"""
URLconf for tests.py usage.

"""
from __future__ import unicode_literals

from django.conf import settings
from django.urls import include, re_path, path
from django.forms import ValidationError
from django.views.generic.base import RedirectView

from . import OPTIONS
from .views import (InboxView, SentView, ArchivesView, TrashView,
        WriteView, ReplyView, MessageView, ConversationView,
        ArchiveView, DeleteView, UndeleteView)
from django.contrib.auth.views import LoginView


# user_filter function set
def user_filter_reason(user):
    if user.get_username() == 'bar':
        return 'some reason'
    return None
def user_filter_no_reason(user):
    return ''
def user_filter_false(user):
    return False
def user_filter_exception(user):
    if user.get_username() == 'bar':
        raise ValidationError(['first good reason', "anyway, I don't like {0}".format(user.get_username())])
    return None

# exchange_filter function set
def exch_filter_reason(sender, recipient, recipients_list):
    if recipient.get_username() == 'bar':
        return 'some reason'
    return None
def exch_filter_no_reason(sender, recipient, recipients_list):
    return ''
def exch_filter_false(sender, recipient, recipients_list):
    return False
def exch_filter_exception(sender, recipient, recipients_list):
    if recipient.get_username() == 'bar':
        raise ValidationError(['first good reason', "anyway, I don't like {0}".format(recipient.get_username())])
    return None

# auto-moderation function set
def moderate_as_51(message):
    return 51
def moderate_as_48(message):
    return (48, "some reason")
moderate_as_48.default_reason = 'some default reason'

# quote formatters
def format_subject(subject):
    return "Re_ " + subject
def format_body(sender, body):
    return "{0} _ {1}".format(sender, body)

postman_patterns = [
    # Basic set
    re_path(r'inbox/(?:(?P<option>'+OPTIONS+')/)?$', InboxView.as_view(), name='inbox'),
    re_path(r'sent/(?:(?P<option>'+OPTIONS+')/)?$', SentView.as_view(), name='sent'),
    re_path(r'archives/(?:(?P<option>'+OPTIONS+')/)?$', ArchivesView.as_view(), name='archives'),
    re_path(r'trash/(?:(?P<option>'+OPTIONS+')/)?$', TrashView.as_view(), name='trash'),
    re_path('write/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(), name='write'),
    path('reply/<int:message_id>/', ReplyView.as_view(), name='reply'),
    path('view/<int:message_id>/', MessageView.as_view(), name='view'),
    path('view/t/<int:thread_id>/', ConversationView.as_view(), name='view_conversation'),
    path('archive/', ArchiveView.as_view(), name='archive'),
    path('delete/', DeleteView.as_view(), name='delete'),
    path('undelete/', UndeleteView.as_view(), name='undelete'),
    path('', RedirectView.as_view(url='inbox/', permanent=True)),

    # Customized set
    # 'success_url'
    re_path(r'^write_sent/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(success_url='postman:sent'), name='write_with_success_url_to_sent'),
    path('reply_sent/<int:message_id>/', ReplyView.as_view(success_url='postman:sent'), name='reply_with_success_url_to_sent'),
    path('archive_arch/', ArchiveView.as_view(success_url='postman:archives'), name='archive_with_success_url_to_archives'),
    path('delete_arch/', DeleteView.as_view(success_url='postman:archives'), name='delete_with_success_url_to_archives'),
    path('undelete_arch/', UndeleteView.as_view(success_url='postman:archives'), name='undelete_with_success_url_to_archives'),
    # 'max'
    re_path(r'^write_max/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(max=1), name='write_with_max'),
    path('reply_max/<int:message_id>/', ReplyView.as_view(max=1), name='reply_with_max'),
    # 'user_filter' on write
    re_path(r'^write_user_filter_reason/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(user_filter=user_filter_reason), name='write_with_user_filter_reason'),
    re_path(r'^write_user_filter_no_reason/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(user_filter=user_filter_no_reason), name='write_with_user_filter_no_reason'),
    re_path(r'^write_user_filter_false/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(user_filter=user_filter_false), name='write_with_user_filter_false'),
    re_path(r'^write_user_filter_exception/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(user_filter=user_filter_exception), name='write_with_user_filter_exception'),
    # 'user_filter' on reply
    path('reply_user_filter_reason/<int:message_id>/', ReplyView.as_view(user_filter=user_filter_reason), name='reply_with_user_filter_reason'),
    path('reply_user_filter_no_reason/<int:message_id>/', ReplyView.as_view(user_filter=user_filter_no_reason), name='reply_with_user_filter_no_reason'),
    path('reply_user_filter_false/<int:message_id>/', ReplyView.as_view(user_filter=user_filter_false), name='reply_with_user_filter_false'),
    path('reply_user_filter_exception/<int:message_id>/', ReplyView.as_view(user_filter=user_filter_exception), name='reply_with_user_filter_exception'),
    # 'exchange_filter' on write
    re_path(r'^write_exch_filter_reason/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(exchange_filter=exch_filter_reason), name='write_with_exch_filter_reason'),
    re_path(r'^write_exch_filter_no_reason/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(exchange_filter=exch_filter_no_reason), name='write_with_exch_filter_no_reason'),
    re_path(r'^write_exch_filter_false/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(exchange_filter=exch_filter_false), name='write_with_exch_filter_false'),
    re_path(r'^write_exch_filter_exception/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(exchange_filter=exch_filter_exception), name='write_with_exch_filter_exception'),
    # 'exchange_filter' on reply
    path('reply_exch_filter_reason/<int:message_id>/', ReplyView.as_view(exchange_filter=exch_filter_reason), name='reply_with_exch_filter_reason'),
    path('reply_exch_filter_no_reason/<int:message_id>/', ReplyView.as_view(exchange_filter=exch_filter_no_reason), name='reply_with_exch_filter_no_reason'),
    path('reply_exch_filter_false/<int:message_id>/', ReplyView.as_view(exchange_filter=exch_filter_false), name='reply_with_exch_filter_false'),
    path('reply_exch_filter_exception/<int:message_id>/', ReplyView.as_view(exchange_filter=exch_filter_exception), name='reply_with_exch_filter_exception'),
    # 'auto_moderators'
    re_path(r'^write_moderate/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(auto_moderators=(moderate_as_51,moderate_as_48)), name='write_moderate'),
    path('reply_moderate/<int:message_id>/', ReplyView.as_view(auto_moderators=(moderate_as_51,moderate_as_48)), name='reply_moderate'),
    # 'formatters'
    path('reply_formatters/<int:message_id>/', ReplyView.as_view(formatters=(format_subject, format_body)), name='reply_formatters'),
    path('view_formatters/<int:message_id>/', MessageView.as_view(formatters=(format_subject, format_body)), name='view_formatters'),
    # auto-complete
    re_path(r'^write_ac/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(autocomplete_channels=('postman_multiple_as1-1', None)), name='write_auto_complete'),
    path('reply_ac/<int:message_id>/', ReplyView.as_view(autocomplete_channel='postman_multiple_as1-1'), name='reply_auto_complete'),
    # 'template_name'
    re_path(r'^inbox_template/(?:(?P<option>'+OPTIONS+')/)?$', InboxView.as_view(template_name='postman/fake.html'), name='inbox_template'),
    re_path(r'^sent_template/(?:(?P<option>'+OPTIONS+')/)?$', SentView.as_view(template_name='postman/fake.html'), name='sent_template'),
    re_path(r'^archives_template/(?:(?P<option>'+OPTIONS+')/)?$', ArchivesView.as_view(template_name='postman/fake.html'), name='archives_template'),
    re_path(r'^trash_template/(?:(?P<option>'+OPTIONS+')/)?$', TrashView.as_view(template_name='postman/fake.html'), name='trash_template'),
    re_path(r'^write_template/(?:(?P<recipients>[^/#]+)/)?$', WriteView.as_view(template_name='postman/fake.html'), name='write_template'),
    path('reply_template/<int:message_id>/', ReplyView.as_view(template_name='postman/fake.html'), name='reply_template'),
    path('view_template/<int:message_id>/', MessageView.as_view(template_name='postman/fake.html'), name='view_template'),
    path('view_template/t/<int:thread_id>/', ConversationView.as_view(template_name='postman/fake.html'), name='view_conversation_template'),
]

urlpatterns = [
    path('accounts/login/', LoginView.as_view()),  # because of the login_required decorator
    path('messages/', include((postman_patterns, 'postman', 'postman'))),  # (<patterns object>, <application namespace>, <instance namespace>)
]

# because of fields.py/AutoCompleteWidget/render()/reverse()
if 'ajax_select' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('ajax_select/', include('ajax_select.urls')),  # django-ajax-selects
    ]

# optional
if 'notification' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('notification/', include('notification.urls')),  # django-notification
    ]
