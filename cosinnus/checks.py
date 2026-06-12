import traceback
from functools import wraps
from typing import Type, Union

from django.core.checks import Error, Info, Warning, register
from django.db import DatabaseError, InterfaceError, OperationalError, ProgrammingError
from django.utils import translation

from cosinnus.conf import settings
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.test import is_db_ready, table_exists

DEFAULT_DB_ERROR_ID = 'myapp.E900'


def get_traceback_without_first_frame(exc: Exception) -> str:
    """
    Formats a traceback from the given exception omitting the first frame.
    Used to not show the wrapper in tracebacks when using decorators.
    """
    tb = exc.__traceback__.tb_next if exc.__traceback__ else None
    return ''.join(traceback.format_exception(type(exc), exc, tb))


def handle_db_errors(
    *,
    id=DEFAULT_DB_ERROR_ID,
    level: Type[Union[Info, Warning, Error]] = Warning,
    msg='Database check could not be completed.',
    hint=('The database may not be initialized yet. Run migrations and ensure the configured database is reachable.'),
    check_name=None,
    include_traceback=True,
):
    """
    Decorator for Django system checks that access the database.

    Converts database initialization/query errors into Django check messages
    instead of crashing manage.py check / startup checks.
    """

    def decorator(check_func):
        @wraps(check_func)
        def wrapper(*args, **kwargs):
            check_ref = check_name or f'{check_func.__module__}.{check_func.__qualname__}'

            try:
                return check_func(*args, **kwargs) or []

            except (ProgrammingError, OperationalError, InterfaceError, DatabaseError) as exc:
                details = [
                    hint,
                    f'Failing check: {check_ref}',
                ]
                if include_traceback:
                    details.append(get_traceback_without_first_frame(exc))

                return [
                    level(
                        msg,
                        hint='\n'.join(details),
                        id=id,
                    )
                ]

        return wrapper

    return decorator


@register()
@handle_db_errors()
def check_unsupported_group_types(app_configs, **kwargs):
    """
    Warns if unsupported cosinnus group types exist in the database.
    """
    # skip if cosinnus is not to be checked
    if app_configs is not None:
        if 'cosinnus' not in [app.label for app in app_configs]:
            return []

    # skip if the database is not initialized
    if not is_db_ready() or not table_exists('cosinnus_cosinnusgroup'):
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

    if len(settings.NEWW_DEFAULT_USER_GROUPS) == 0:
        errors.append(Warning('NEWW_DEFAULT_USER_GROUPS is empty. Expect UI breakage.'))

    return errors
