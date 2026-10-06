"""Rendering helpers for inactivity warning emails."""

from datetime import timedelta
from typing import Literal, Optional, Tuple

from babel import Locale
from babel.dates import format_timedelta
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import force_str

INACTIVITY_DURATION_UNITS = ('day', 'week', 'month', 'year')


def format_inactivity_duration(days: int, config, language: str) -> str:
    """
    Use an explicit text override or format a duration with Babel.

    Rounds to given 'display_unit'.  Falls back to 'day' if not set.
    """
    if 'text' in config and config['text'] is not None:
        with translation.override(language):
            return force_str(config['text'])

    unit = config.get('display_unit', 'day')
    if unit not in INACTIVITY_DURATION_UNITS:
        raise ImproperlyConfigured(f'Unknown inactivity duration unit: {unit}')

    # convert django language code to babel locale
    locale = Locale.parse(language, sep='-')

    # An infinite threshold prevents Babel from promoting the explicitly configured unit to a larger one.
    return format_timedelta(timedelta(days=days), granularity=unit, threshold=float('inf'), locale=locale)


def render_inactivity_mail(
    kind: Literal['user', 'group'],
    recipient,
    days_before_deactivation: int,
    context=None,
    *,
    language_override: Optional[str] = None,
) -> Tuple[str, str]:
    """Render a localized warning email using the settings for user/group inactivity schedule."""
    if kind == 'user':
        config = settings.COSINNUS_USER_INACTIVITY_SCHEDULE
        deletion_days = settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS
    else:
        config = settings.COSINNUS_GROUP_INACTIVITY_SCHEDULE
        deletion_days = settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS

    warning = config['warnings'][days_before_deactivation]

    profile = getattr(recipient, 'cosinnus_profile', None)
    language = language_override or getattr(profile, 'language', None) or settings.LANGUAGE_CODE
    deactivation_in = format_inactivity_duration(days_before_deactivation, warning, language)
    deactivation_after = format_inactivity_duration(config['days'], config, language)

    template_context = dict(
        context or {},
        user=recipient,
        language=language,
        days_before_deactivation=days_before_deactivation,
        deleted_after_days=deletion_days,
        deactivation_in=deactivation_in,
        inactivity_days=config['days'],
        deactivation_after=deactivation_after,
    )

    with translation.override(language):
        subject = render_to_string(warning['subject_template'], template_context).strip()
        # Email headers must not contain line breaks.
        subject = ' '.join(subject.splitlines())
        body = render_to_string(warning['body_template'], template_context)

    return subject, body
