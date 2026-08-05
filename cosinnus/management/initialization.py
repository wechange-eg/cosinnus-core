from django.apps import apps as global_apps
from django.contrib.sites.management import create_default_site
from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connections, router

from cosinnus.conf import settings


def ensure_portal_and_site_exist(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    """
    Creates the default CosinnusPortal object. An does a sequence reset to ensure a portal with pk==1 is always present.

    - Is called during and after migrations.

    taken from django/contrib/sites/management and adapted for CosinnusPortal:
    https://github.com/django/django/blob/030c63d329c4814da221528e823a4aaaaa40e4f1/django/contrib/sites/management.py
    """

    # make sure, site exists
    create_default_site(app_config, verbosity=verbosity, interactive=interactive, using=using, apps=apps, **kwargs)

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
        CosinnusPortal(pk=1, name='default portal', slug='default', public=True, site_id=1).save(using=using)

        # We set an explicit pk instead of relying on auto-incrementation,
        # so we need to reset the database sequence. See #17415.
        sequence_sql = connections[using].ops.sequence_reset_sql(no_style(), [CosinnusPortal])
        if sequence_sql:
            if verbosity >= 2:
                print('Resetting sequence')
            with connections[using].cursor() as cursor:
                for command in sequence_sql:
                    cursor.execute(command)


def ensure_default_portal_conference_settings_exist(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    """
    Creates a CosinnusConferenceSettings Object for the current portal if it does not exist.
    Sets the defaults to a valid state for the top-level CosinnusConferenceSettings
    as far as the current Model state allows.

    - Does not do a Sequence reset.
    - Is called during and after migrations.
    """
    CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
    CosinnusConferenceSettings = apps.get_model('cosinnus', 'CosinnusConferenceSettings')
    current_portal = CosinnusPortal.objects.using(using).get(site__id=settings.SITE_ID)
    ContentType = apps.get_model('contenttypes', 'ContentType')
    portal_content_type = ContentType.objects.get_for_model(CosinnusPortal)

    if not current_portal or not portal_content_type:
        return

    # valid defaults need to be set explicitly; bbb-tests will fail otherwise
    # defaults differ between dummy model and real model and not all default fields are available everytime
    # determine applicable default fields from the current CosinnusConferenceSettings model
    defaults = {'bbb_server_choice': 0, 'bbb_server_choice_premium': 0}
    available_fields = {f.name for f in CosinnusConferenceSettings._meta.get_fields()}
    applicable_defaults = {k: v for k, v in defaults.items() if k in available_fields}

    obj, created = CosinnusConferenceSettings.objects.using(using).get_or_create(
        content_type=portal_content_type, object_id=current_portal.id, defaults=applicable_defaults
    )

    # force saving for the overwritten save-method of the model
    if created:
        try:
            obj.save(using=using, ignore_inherit_condition=True)
        except TypeError:
            # we have the dummy model, so the object is already saved
            pass


# registered as receiver for `post_migration` in cosinnus.apps.CosinnusAppConfig.ready
def ensure_current_portal_object(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    """make sure, the current portal object exists and do the same for related objects"""
    ensure_portal_and_site_exist(app_config, verbosity, interactive, using, apps, **kwargs)
    ensure_default_portal_conference_settings_exist(app_config, verbosity, interactive, using, apps, **kwargs)
