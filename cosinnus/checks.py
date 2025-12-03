from django.core.checks import Error, Warning, register
from django.utils import translation

from cosinnus.conf import settings
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.utils.group import get_cosinnus_group_model


@register()
def check_unsupported_group_types(app_configs, **kwargs):
    """
    Warns if unsupported cosinnus group types exist in the database.
    """
    # skip if cosinnus is not to be checked
    if app_configs is not None:
        if 'cosinnus' not in [app.label for app in app_configs]:
            return []

    group_model = get_cosinnus_group_model()
    types = dict(group_model.TYPE_CHOICES)
    types_supported = group_model_registry.group_type_index.keys()
    types_unsupported = types.keys() - types_supported

    warnings = []
    with translation.override(None):
        for _type in types_unsupported:
            if group_model.objects.filter(type=_type, is_active=True).exists():
                warnings.append(
                    Warning(
                        f'Unsupported group type present: {types[_type]}',
                        hint=(
                            'Database contains group types unsupported by current configuration. '
                            'This may cause crashes.'
                        ),
                        id='cosinnus.W001',
                        obj=group_model,
                    )
                )
    return warnings


@register()
def check_settings(app_configs, **kwargs):
    """Check settings"""
    errors = []
    if settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED and not settings.COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME:
        errors.append(
            Error(
                'COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME must be enabled to enable '
                'COSINNUS_USER_FORM_LAST_NAME_REQUIRED.'
            )
        )
    return errors
