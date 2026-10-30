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

from cosinnus.models import CosinnusPortal

INACTIVITY_DURATION_UNITS = ('day', 'week', 'month', 'year')


def format_inactivity_duration(days: int, config, language: str, *, add_direction: bool = False) -> str:
    """
    Use the explicit 'text' or 'relative_text' override, depending on add_direction, or format with Babel.

    Rounds to given 'display_unit' and optionally adds past/future direction. Falls back to 'day' if not set.
    For example, add_direction=True formats 10 days as "in 10 Tagen" instead of "10 Tage" in German.
    """
    override_key = 'relative_text' if add_direction else 'text'
    override = config.get(override_key)
    if override is not None:
        with translation.override(language):
            return force_str(override)

    unit = config.get('display_unit', 'day')
    if unit not in INACTIVITY_DURATION_UNITS:
        raise ImproperlyConfigured(f'Unknown inactivity duration unit: {unit}')

    # convert django language code to babel locale
    locale = Locale.parse(language, sep='-')

    # An infinite threshold prevents Babel from promoting the explicitly configured unit to a larger one.
    return format_timedelta(
        timedelta(days=days),
        granularity=unit,
        threshold=float('inf'),
        add_direction=add_direction,
        locale=locale,
    )


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
    # Keep the warning period neutral for templates that describe the remaining duration.
    warning_period = format_inactivity_duration(days_before_deactivation, warning, language)
    # Include the localized future direction because templates use this as a complete relative time expression.
    relative_warning_period = format_inactivity_duration(
        days_before_deactivation, warning, language, add_direction=True
    )
    # Keep the inactivity period neutral so templates can place it relative to the last activity.
    inactivity_period = format_inactivity_duration(config['days'] - days_before_deactivation, config, language)

    template_context = dict(
        context or {},
        user=recipient,
        language=language,
        days_before_deactivation=days_before_deactivation,
        deleted_after_days=deletion_days,
        warning_period=warning_period,
        relative_warning_period=relative_warning_period,
        inactivity_days=config['days'],
        inactivity_period=inactivity_period,
        support_email=CosinnusPortal.get_current().support_email,
        portal_name=CosinnusPortal.get_current().name,
    )

    with translation.override(language):
        subject = render_to_string(warning['subject_template'], template_context).strip()
        # Email headers must not contain line breaks.
        subject = ' '.join(subject.splitlines())
        body = render_to_string(warning['body_template'], template_context)

    return subject, body
