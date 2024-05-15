from rest_framework.exceptions import ValidationError

from cosinnus.api_frontend.handlers.error_codes import (
    ERROR_SIGNUP_MTAG_REQUIRED,
    ERROR_SIGNUP_MTAG_UNKNOWN,
    ERROR_SIGNUP_ONLY_ONE_MTAG_ALLOWED,
)
from cosinnus.conf import settings
from cosinnus.models.managed_tags import CosinnusManagedTag


def validate_managed_tag_slugs(managed_tag_slugs, at_least_one_tag_required):
    """Check if a given list of managed tag slugs is valid for saving in a form,
    checking missing, too many and valid managed tags."""
    if not managed_tag_slugs and at_least_one_tag_required:
        raise ValidationError(ERROR_SIGNUP_MTAG_REQUIRED)
    if len(managed_tag_slugs) > 1 and not settings.COSINNUS_MANAGED_TAGS_ASSIGN_MULTIPLE_ENABLED:
        raise ValidationError(ERROR_SIGNUP_ONLY_ONE_MTAG_ALLOWED)
    all_mtag_slugs = set([mtag.slug for mtag in CosinnusManagedTag.objects.all_in_portal_cached()])
    unknown_tags = set(managed_tag_slugs).difference(all_mtag_slugs)
    if len(unknown_tags) > 0:
        raise ValidationError(ERROR_SIGNUP_MTAG_UNKNOWN % ', '.join(unknown_tags))
