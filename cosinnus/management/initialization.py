"""
Creates the default CosinnusPortal object.
taken from django/contrib/sites/management and adapted for CosinnusPortal:
https://github.com/django/django/blob/030c63d329c4814da221528e823a4aaaaa40e4f1/django/contrib/sites/management.py
"""

from django.apps import apps as global_apps
from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connections, router


def create_default_portal(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    try:
        CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
    except LookupError:
        return

    if not router.allow_migrate_model(using, CosinnusPortal):
        return

    if not CosinnusPortal.objects.using(using).exists():
        # The default settings set SITE_ID = 1, and some tests in Django's test
        # suite rely on this value. However, if database sequences are reused
        # (e.g. in the test suite after flush/syncdb), it isn't guaranteed that
        # the next id will be 1, so we coerce it. See #15573 and #16353. This
        # can also crop up outside of tests - see #15346.

        # This is also done für CosinnusPortal_id.

        if verbosity >= 2:
            print('Creating default CosinnusPortal object')
        CosinnusPortal(pk=1, name='default portal', slug='default', site_id=1).save(using=using)

        # We set an explicit pk instead of relying on auto-incrementation,
        # so we need to reset the database sequence. See #17415.
        sequence_sql = connections[using].ops.sequence_reset_sql(no_style(), [CosinnusPortal])
        if sequence_sql:
            if verbosity >= 2:
                print('Resetting sequence')
            with connections[using].cursor() as cursor:
                for command in sequence_sql:
                    cursor.execute(command)
