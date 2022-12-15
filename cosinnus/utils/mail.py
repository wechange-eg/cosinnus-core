from django.template.loader import render_to_string
from django.urls import reverse

from cosinnus.core.mail import send_mail_or_fail_threaded, get_html_mail_data,\
    send_mail_or_fail
from cosinnus.models.group import CosinnusPortal


def send_notification_item_html(to_user, subject, context, notification_reason=None, template='cosinnus/html_mail/summary_item.html', extra_data=dict):
    """
    Send notification item mail using context given
    """
    notification_item_html = render_to_string(template, context)
    data = get_html_mail_data(to_user, subject, notification_item_html, use_notification_item_html=True)
    if notification_reason:
        data.update({
            'notification_reason': notification_reason,
            'prefs_url': f"{CosinnusPortal.get_current().get_domain()}{reverse('cosinnus:notifications')}", # workaround to get the template's `{{prefs_url}}` work properly
        })
    if extra_data:
        data.update(extra_data)
    mail_template = '/cosinnus/html_mail/notification.html'
    return send_mail_or_fail(to_user.email, subject, mail_template, data, is_html=True)


def send_notification_item_html_threaded(to_user, subject, context, notification_reason=None, template='cosinnus/html_mail/summary_item.html'):
    """
    Send notification item mail using context given
    """
    notification_item_html = render_to_string(template, context)
    data = get_html_mail_data(to_user, subject, notification_item_html, use_notification_item_html=True)
    if notification_reason:
        data.update({
            'notification_reason': notification_reason,
            'prefs_url': f"{CosinnusPortal.get_current().get_domain()}{reverse('cosinnus:notifications')}", # workaround to get the template's `{{prefs_url}}` work properly
        })
    mail_template = '/cosinnus/html_mail/notification.html'
    return send_mail_or_fail_threaded(to_user.email, subject, mail_template, data, is_html=True)
