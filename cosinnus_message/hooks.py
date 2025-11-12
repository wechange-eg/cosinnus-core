from django.dispatch import receiver

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.models import get_user_profile_model
from cosinnus.utils.user import is_user_active
from cosinnus_message.integration import ROCKET_SINGLETON

if settings.COSINNUS_ROCKET_ENABLED:
    if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_RESTRICT_ROCKETCHAT_ACCOUNT_DISABLED:

        @receiver(signals.managed_tags_changed)
        def handle_managed_tags_rocket_account_disable(sender, obj, tag_slugs_added, tag_slugs_removed, **kwargs):
            """Listen to managed tag changes to activate/deactivate rocketchat accounts set in
            `COSINNUS_MANAGED_TAGS_RESTRICT_ROCKETCHAT_ACCOUNT_DISABLED`."""

            if isinstance(obj, get_user_profile_model()):
                profile = obj
                # check if a restricted tag was either added or removed
                if any(
                    [
                        tagslug in tag_slugs_added
                        for tagslug in settings.COSINNUS_MANAGED_TAGS_RESTRICT_ROCKETCHAT_ACCOUNT_DISABLED
                    ]
                ) or any(
                    [
                        tagslug in tag_slugs_removed
                        for tagslug in settings.COSINNUS_MANAGED_TAGS_RESTRICT_ROCKETCHAT_ACCOUNT_DISABLED
                    ]
                ):
                    # do not trust the signal changeset and instead the current state of the userprofile managed tags
                    user_tagslugs = profile.get_managed_tag_slugs()
                    restricted_tag_contained = any(
                        [
                            tagslug in settings.COSINNUS_MANAGED_TAGS_RESTRICT_BBB_NO_CREATE_ROOMS
                            for tagslug in user_tagslugs
                        ]
                    )
                    if restricted_tag_contained:
                        # deactivate the rocketchat user account if a restricted tag is assigned to the user profile
                        ROCKET_SINGLETON.do_user_deactivate(profile.user)
                    elif is_user_active(profile.user):
                        # activate the rocketchat user account if no restricted tag is assigned to the user profile
                        # and the user account is active
                        ROCKET_SINGLETON.do_user_activate(profile.user)
