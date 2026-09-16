"""Rendering helpers for inactivity warning emails."""

import logging
from datetime import timedelta
from typing import Literal, Optional, Tuple

from babel import Locale, UnknownLocaleError
from babel.dates import format_timedelta
from django.conf import settings
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import force_str

logger = logging.getLogger('cosinnus')

INACTIVITY_DURATION_UNITS = ('day', 'week', 'month', 'year')

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


def format_inactivity_duration(days: int, config, language: str) -> str:
    """Use an explicit text override or format a duration with Babel."""
    if 'text' in config and config['text'] is not None:
        with translation.override(language):
            return force_str(config['text'])

    unit = config.get('unit', 'day')
    if unit not in INACTIVITY_DURATION_UNITS:
        logger.warning('Unknown inactivity duration unit %s; formatting duration as days.', unit)
        unit = 'day'

    try:
        locale = Locale.parse(language, sep='-')
    except (UnknownLocaleError, ValueError):
        logger.warning('Cannot localize inactivity duration for language %s; using English.', language)
        locale = Locale('en')

    # An infinite threshold prevents Babel from promoting the explicitly configured unit to a larger one.
    return format_timedelta(timedelta(days=days), granularity=unit, threshold=float('inf'), locale=locale)


def render_inactivity_mail(
    kind: Literal['user', 'group'],
    recipient,
    days_before_deactivation: int,
    context,
    *,
    language_override: Optional[str] = None,
    template_info: Optional[dict] = None,
) -> Tuple[str, str]:
    """Render a localized warning; optionally record effective template paths and fallback status for previews."""
    if kind == 'user':
        config = settings.COSINNUS_USER_INACTIVITY
    else:
        config = settings.COSINNUS_GROUP_INACTIVITY

    warning = config['warnings'][days_before_deactivation]

    profile = getattr(recipient, 'cosinnus_profile', None)
    language = language_override or getattr(profile, 'language', None) or 'en'
    warning_text = format_inactivity_duration(days_before_deactivation, warning, language)
    inactivity_text = format_inactivity_duration(config['days'], config, language)

    template_context = dict(
        context,
        user=recipient,
        language=language,
        days_before_deactivation=days_before_deactivation,
        warning_text=warning_text,
        inactivity_days=config['days'],
        inactivity_text=inactivity_text,
    )

    configured_templates = (warning.get('subject_template'), warning.get('body_template'))
    default_templates = DEFAULT_TEMPLATES[kind]
    used_templates = default_templates
    result = None

    with translation.override(language):
        # Use custom templates if available and not default, fallback to core templates on error
        if all(configured_templates) and configured_templates != default_templates:
            try:
                result = _render_template_pair(*configured_templates, template_context)
                used_templates = configured_templates
            except (TemplateDoesNotExist, TemplateSyntaxError):
                logger.warning(
                    'Cannot render inactivity mail templates %s and %s; using fallback.',
                    *configured_templates,
                    exc_info=True,
                )
        if result is None:
            result = _render_template_pair(*default_templates, template_context)
    if template_info is not None:
        template_info.update(
            subject_template=used_templates[0],
            body_template=used_templates[1],
            fallback=used_templates != configured_templates,
        )
    return result
