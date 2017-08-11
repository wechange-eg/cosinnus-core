from datetime import date

from django.utils import six
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36


class EmailBlacklistTokenGenerator(object):
    """
    Strategy object used to generate and check tokens for the list-unsubscribe email blacklist mechanism.
    
    Taken and modified from `django.contrib.auth.tokens.PasswordResetTokenGenerator`. 
    Note: This does not actually use any information that isn't accessible to the user 
    (only the timestamp and email are used for token generation), so this is *not* a secure token!
    
    However since we use it only as a permission to blacklist an email, *and* it needs to be available
    for non-registered users, and we do not want to persist tokens for this in the DB,
    we think it is an acceptable compromise as an alternative to having a "naked" unsubscribe URL,
    where anyone could unsubscribe an email at their leisure.
    """
    def make_token(self, email):
        """
        Returns a token that can be forever to do a password reset
        for the given email.
        """
        return self._make_token_with_timestamp(email, self._num_days(self._today()))

    def check_token(self, email, token):
        """
        Check that a password reset token is correct for a given email.
        """
        # Parse the token
        try:
            ts_b36, hash = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(email, ts), token):
            return False

        return True

    def _make_token_with_timestamp(self, email, timestamp):
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)

        # By hashing on the internal state of the user and using state
        # that is sure to change (the password salt will change as soon as
        # the password is set, at least for current Django auth, and
        # last_login will also change), we produce a hash that will be
        # invalid as soon as it is used.
        # We limit the hash to 20 chars to keep URL short
        key_salt = "cosinnus.core.utils.tokens.EmailBlacklistTokenGenerator"

        value = (email + six.text_type(timestamp))
        hash = salted_hmac(key_salt, value).hexdigest()[::2]
        return "%s-%s" % (ts_b36, hash)

    def _num_days(self, dt):
        return (dt - date(2001, 1, 1)).days

    def _today(self):
        # Used for mocking in tests
        return date.today()


email_blacklist_token_generator = EmailBlacklistTokenGenerator()
