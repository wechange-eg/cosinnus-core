"""Rendering helpers for inactivity warning emails."""

import logging
from typing import Literal, Optional, Tuple

from django.conf import settings
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils import translation

logger = logging.getLogger('cosinnus')

DEFAULT_TEMPLATES = {
    'user': (
        'cosinnus/mail/inactivity/user_subject.txt',
        'cosinnus/mail/inactivity/user_body.txt',
    ),
    'group': (
        'cosinnus/mail/inactivity/group_subject.txt',
        'cosinnus/mail/inactivity/group_body.txt',
    ),
}


def _render_template_pair(subject_template, body_template, context):
    subject = render_to_string(subject_template, context).strip()
    body = render_to_string(body_template, context)
    # Email headers must not contain line breaks.
    return ' '.join(subject.splitlines()), body


def render_inactivity_mail(
    kind: Literal['user', 'group'],
    recipient,
    days_before_deactivation: int,
    context,
    *,
    language_override: Optional[str] = None,
) -> Tuple[str, str]:
    """Render a localized inactivity warning, falling back to the core templates."""
    if kind == 'user':
        config = settings.COSINNUS_USER_INACTIVITY
    else:
        config = settings.COSINNUS_GROUP_INACTIVITY

    warning = config['warnings'][days_before_deactivation]

    profile = getattr(recipient, 'cosinnus_profile', None)
    language = language_override or getattr(profile, 'language', None) or 'en'

    template_context = dict(
        context,
        user=recipient,
        language=language,
        days_before_deactivation=days_before_deactivation,
        warning_text=warning['text'],
        inactivity_days=config['days'],
        inactivity_text=config['text'],
    )

    configured_templates = (warning.get('subject_template'), warning.get('body_template'))
    default_templates = DEFAULT_TEMPLATES[kind]

    with translation.override(language):
        # Use custom templates if available and not default, fallback to core templates on error
        if all(configured_templates) and configured_templates != default_templates:
            try:
                return _render_template_pair(*configured_templates, template_context)
            except (TemplateDoesNotExist, TemplateSyntaxError):
                logger.warning(
                    'Cannot render inactivity mail templates %s and %s; using fallback.',
                    *configured_templates,
                    exc_info=True,
                )
        return _render_template_pair(*default_templates, template_context)
