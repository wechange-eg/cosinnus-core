from django.template.loader import render_to_string

from cosinnus.core.mail import send_mail_or_fail_threaded, get_html_mail_data,\
    send_mail_or_fail


def send_notification_item_html(to_user, subject, context, template='cosinnus/html_mail/summary_item.html'):
    """
    Send notification item mail using context given
    """
    notification_item_html = render_to_string(template, context)
    data = get_html_mail_data(to_user, subject, notification_item_html, use_notification_item_html=True)
    mail_template = '/cosinnus/html_mail/notification.html'
    return send_mail_or_fail(to_user.email, subject, mail_template, data, is_html=True)


def send_notification_item_html_threaded(to_user, subject, context, template='cosinnus/html_mail/summary_item.html'):
    """
    Send notification item mail using context given
    """
    notification_item_html = render_to_string(template, context)
    data = get_html_mail_data(to_user, subject, notification_item_html, use_notification_item_html=True)
    mail_template = '/cosinnus/html_mail/notification.html'
    return send_mail_or_fail_threaded(to_user.email, subject, mail_template, data, is_html=True)
