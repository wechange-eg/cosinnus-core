from django.core.checks import Error, register

from cosinnus.conf import settings


@register()
def check_settings(app_configs, **kwargs):
    """Check settings"""
    errors = []
    if settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED and not settings.COSINNUS_CLOUD_ENABLED:
        errors.append(Error('COSINNUS_CLOUD_ENABLED must be True to enable COSINNUS_EVENT_V3_CALENDAR_ENABLED.'))
    return errors
