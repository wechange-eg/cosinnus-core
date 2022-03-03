import six
from django.template.loader import render_to_string
from django.utils.html import escape


def get_organization_select2_pills(organizations, text_only=False):
    return [(
         "organization:" + six.text_type(org.id),
         render_to_string('cosinnus/organization/organization_select2_pill.html', {'text': escape(org.name)}).replace('\n', '').replace('\r', '') if not text_only else escape(org.name),
         ) for org in organizations]
