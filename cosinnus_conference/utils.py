from datetime import datetime
import re

from django.conf import settings
from django.template import Template, Context
from django.template.loader import get_template
from django.utils import translation, timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from cosinnus.core.mail import get_common_mail_context
from cosinnus.utils.files import get_image_url_for_icon
from cosinnus.utils.mail import send_notification_item_html_threaded,\
    send_notification_item_html
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.user import filter_active_users
from cosinnus.utils.permissions import check_user_can_receive_emails
from uritemplate.api import variables
from django.template.defaultfilters import date
from cosinnus.utils.html import render_html_with_variables


def get_initial_template(field_name):
    """
    Get template for subject/content of conference reminder emails
    """
    content_template_name = 'cosinnus/mail/conference_reminder_%s.txt'
    template = get_template(content_template_name % field_name)
    return template.render({})  # render to trigger translate


def send_conference_reminder(group, recipients=None, field_name="week_before", update_setting=True):
    """
    Send conference reminder email a week/day/hour before start
    """
    def render_template(dynamic_fields, field_name, field_type, user, group):
        template = dynamic_fields.get(f'reminder_{field_name}_{field_type}')
        template = template or get_initial_template(f'{field_name}_{field_type}')
        variables = {
            'name': group['name'],
            'from_date': date(timezone.localtime(group.from_date), 'SHORT_DATETIME_FORMAT'),
            'to_date': date(timezone.localtime(group.to_date), 'SHORT_DATETIME_FORMAT'),
        }
        return render_html_with_variables(user, template, variables)
    
    if not recipients:
        recipients = group.actual_members
    
    for recipient in recipients:
        if not check_user_can_receive_emails(recipient):
            continue
        
        # switch language to user's preference language
        cur_language = translation.get_language()
        try:
            if hasattr(recipient, 'cosinnus_profile'):  # receiver can be a virtual user
                translation.activate(getattr(recipient.cosinnus_profile, 'language', settings.LANGUAGES[0][0]))

            dynamic_fields = group.dynamic_fields or {}
            subject = render_template(dynamic_fields, field_name, 'subject', recipient, group)
            content = textfield(render_template(dynamic_fields, field_name, 'content', recipient, group))

            portal_url = group.portal.get_domain()
            group_icon_url = portal_url + (group.get_avatar_thumbnail_url() or get_image_url_for_icon(group.get_icon()))
            context = {
                'action_user_url': group.get_absolute_url(),
                'user_image_url': group_icon_url,
                'action_user_name': group.name,
                'object_url': group.get_absolute_url(),
                'object_icon_url': group_icon_url,
                'object_text': content,
                'show_action_buttons': True,
                'action_button_1_text': _('Go to conference'),
                'action_button_1_url': group.get_absolute_url(),
            }
            send_notification_item_html(recipient, subject, context)
        finally:
            translation.activate(cur_language)

    # Update sent setting
    if update_setting:
        if not group.settings:
            group.settings = {}
        group.settings[f'reminder_{field_name}_sent'] = force_text(datetime.now())
        group.save(update_fields=['settings', ])
