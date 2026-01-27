from django.core.checks import Error, register

from cosinnus.conf import settings


@register()
def check_settings(app_configs, **kwargs):
    """Check settings"""
    errors = []
    if not getattr(settings, 'COSINNUS_CLOUD_ENABLED', False):
        errors.append(Error('COSINNUS_CLOUD_ENABLED must be True if the cosinnus_deck app is enabled.'))
    return errors
