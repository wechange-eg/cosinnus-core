from datetime import datetime

from django.template import Context, Template
from django.template.loader import get_template
from django.utils.encoding import force_text

from cosinnus.core.mail import send_html_mail_threaded


def get_initial_template(field_name):
    """
    Get template for subject/content of conference reminder emails
    """
    content_template_name = 'cosinnus/mail/conference_reminder_%s.txt'
    template = get_template(content_template_name % field_name)
    # FIXME: Remove translation feature
    template = template.template.source.replace('{% load i18n %}', '')
    template = template.replace('{% blocktrans %}', '').replace('{% endblocktrans %}', '')
    return template


def send_conference_reminder(conference, recipients=None, field_name="week_before", update_setting=True):
    """
    Send conference reminder email a week/day/hour before start
    """
    if not recipients:
        recipients = conference.users.filter(is_active=True)
    for recipient in recipients:
        extra_fields = conference.extra_fields or {}
        context = Context({'conference': conference})

        subject = extra_fields.get(f'reminder_{field_name}_subject')
        subject = subject or get_initial_template(f'{field_name}_subject')
        subject = Template(subject).render(context)
        content = extra_fields.get(f'reminder_{field_name}_content')
        content = content or get_initial_template(f'{field_name}_content')
        content = Template(content).render(context)

        send_html_mail_threaded(recipient, subject, content)

    # Update sent setting
    if update_setting:
        if not conference.settings:
            conference.settings = {}
        conference.settings[f'reminder_{field_name}_sent'] = force_text(datetime.now())
        conference.save(update_fields=['settings', ])
