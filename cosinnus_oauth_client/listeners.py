from allauth.socialaccount.signals import social_account_added, social_account_removed
from django.contrib import messages
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from cosinnus.core.mail import get_common_mail_context, send_html_mail_threaded
from cosinnus.templatetags.cosinnus_tags import textfield


def send_disconnect_mail(user, provider, request):
    data = get_common_mail_context(request)
    data.update({'user': user, 'provider': provider})
    subj_user = render_to_string('cosinnus_oauth_client/mail/notification_after_oauth_account_disconnect.txt', data)
    text = textfield(
        render_to_string('cosinnus_oauth_client/mail/notification_after_oauth_account_disconnect.html', data)
    )
    send_html_mail_threaded(user, subj_user, text)


def send_connect_mail(user, provider, request):
    data = get_common_mail_context(request)
    data.update({'user': user, 'provider': provider})
    subj_user = render_to_string('cosinnus_oauth_client/mail/notification_after_oauth_account_connect.txt', data)
    text = textfield(render_to_string('cosinnus_oauth_client/mail/notification_after_oauth_account_connect.html', data))
    send_html_mail_threaded(user, subj_user, text)


@receiver(social_account_added)
def notify_user_on_successfull_connect(sender, **kwargs):
    request = kwargs.get('request')
    messages.add_message(request, messages.SUCCESS, _('Successfully connected account.'))
    user = request.user
    provider = kwargs.get('sociallogin').account.provider
    send_connect_mail(user, provider, request)


@receiver(social_account_removed)
def notify_user_on_successfull_disconnect(sender, **kwargs):
    request = kwargs.get('request')
    messages.add_message(request, messages.SUCCESS, _('Successfully removed connection.'))

    user = request.user
    provider = kwargs.get('socialaccount').provider
    send_disconnect_mail(user, provider, request)
