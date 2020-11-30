from datetime import datetime
import re

from django.template import Template, Context
from django.template.loader import get_template
from django.utils.encoding import force_text

from cosinnus.core.mail import send_html_mail_threaded, get_common_mail_context


def get_initial_template(field_name):
    """
    Get template for subject/content of conference reminder emails
    """
    content_template_name = 'cosinnus/mail/conference_reminder_%s.txt'
    template = get_template(content_template_name % field_name)
    return template.render({})  # render to trigger translate


def send_conference_reminder(conference, recipients=None, field_name="week_before", update_setting=True):
    """
    Send conference reminder email a week/day/hour before start
    """
    def render_template(extra_fields, field_name, field_type, context):
        template = extra_fields.get(f'reminder_{field_name}_{field_type}')
        template = template or get_initial_template(f'{field_name}_{field_type}')
        template = re.sub('\%\(([^\)]+)\)', r'{{\1}}', template)
        return Template(template).render(Context(context))
    if not recipients:
        recipients = conference.users.filter(is_active=True)
    for recipient in recipients:
        extra_fields = conference.extra_fields or {}
        context = get_common_mail_context(request=None, group=conference, user=recipient)

        subject = render_template(extra_fields, field_name, 'subject', context)
        content = render_template(extra_fields, field_name, 'content', context)
        send_html_mail_threaded(recipient, subject, content)

    # Update sent setting
    if update_setting:
        if not conference.settings:
            conference.settings = {}
        conference.settings[f'reminder_{field_name}_sent'] = force_text(datetime.now())
        conference.save(update_fields=['settings', ])
