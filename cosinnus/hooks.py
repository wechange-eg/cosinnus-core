from django.contrib.auth import get_user_model

from cosinnus.conf import settings


def get_full_name_extended(self, force=False):
    """
    Extend the user model's get_full_name function so that it uses the UserProfile's get_full_name function
    if a profile exists.
    This means that both `user.get_full_name()` and `user.cosinnus_profile.get_full_name()` will always
    use the same code in determining the user's displayed name, if the user is a proper one with a profile.
    """
    if hasattr(self, 'cosinnus_profile') and self.cosinnus_profile:
        return self.cosinnus_profile.get_full_name(force=force)
    # fall back to django's default function
    full_name = '%s %s' % (self.first_name, self.last_name)
    return full_name.strip()


setattr(get_user_model(), 'get_full_name', get_full_name_extended)


def is_guest(self):
    """
    Extend the user model with an `is_guest` property, that gets the state from `BaseUserProfile.is_guest`.
    This property cannot be set.

    A user without a cosinnus_profile defaults to is_guest=False.
    """
    # if the initial flag was patched onto the user during account creation, use that
    if hasattr(self, '_initial_is_guest'):
        return self._initial_is_guest
    # otherwise retrieve the flag from the user's cosinnus_profile
    if hasattr(self, 'cosinnus_profile') and self.cosinnus_profile:
        return self.cosinnus_profile._is_guest
    return False


setattr(get_user_model(), 'is_guest', property(is_guest))


def is_account_verified(self):
    """
    Extend the user model with an `is_account_verified` property, that returns if the user is a logged in user
    with `cosinnus_profile.account_verified = True` (if that feature is enabled, otherwise always True when logged in).

    A user without a cosinnus_profile defaults to is_account_verified=False.
    """
    from cosinnus.models import CosinnusPortal

    # otherwise retrieve the flag from the user's cosinnus_profile
    if self.is_authenticated and hasattr(self, 'cosinnus_profile') and self.cosinnus_profile:
        if (
            settings.COSINNUS_USER_ACCOUNTS_NEED_VERIFICATION_ENABLED
            and CosinnusPortal.get_current().accounts_need_verification
            and not self.cosinnus_profile.account_verified
        ):
            return False
        return True
    return False


setattr(get_user_model(), 'is_account_verified', property(is_account_verified))
