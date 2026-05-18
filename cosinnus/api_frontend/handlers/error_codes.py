from django.utils.translation import gettext_lazy as _

# add here all error codes as they will be used in the frontend translation files.
# format: ERROR_NAME = (int:error_code, str:error_message
#     error_code: an int code for errors. the thousand digits are used as a category, the single digits as error code
#       counter. For example: any code in 1*** is login-related
#     error_message: string that is only used as a display in the API and never shown to the user

ERROR_LOGIN_INCORRECT_CREDENTIALS = _('Please enter a correct email and password.')
# ERROR_LOGIN_USER_DISABLED = 'User is disabled'
ERROR_LOGIN_USER_DISABLED = ERROR_LOGIN_INCORRECT_CREDENTIALS  # we show disabled users as wrong credentials
ERROR_LOGIN_USER_NOT_ADMIN_APPROVED = _(
    "Your registration hasn't been confirmed yet. We'll let you know via email as soon as it's ready."
)
ERROR_LOGIN_USER_EMAIL_NOT_VERIFIED = (
    _('New verification email sent!')
    + '\n\n'
    + _(
        'You need to verify your email before logging in. We have just sent you an email with a verifcation '
        "link. Please check your inbox, and if you haven't received an email, please check your spam folder."
    )
    + '\n\n'
    + _(
        'We have just now sent another email with a new verification link to you. If the email still has not '
        'arrived, you may log in again to receive yet another new email.'
    )
)
ERROR_LOGIN_USER_RATELIMIT_HIT = _(
    'You have tried to log in too many times. You may try to log in again in: %(duration)s.'
)
ERROR_LOGIN_NO_COOKIES = _(
    "Your Web browser doesn't appear to have cookies enabled. Cookies are required for logging in."
)
ERROR_LOGIN_FIELD_REQUIRED = _('This field may not be blank.')
ERROR_LOGIN_INVALID_EMAIL_ADDRESS = _('Enter a valid email address.')

ERROR_SIGNUP_EMAIL_IN_USE = 'Email is already in use'
ERROR_SIGNUP_CAPTCHA_INVALID = 'The captcha was not filled or was invalid'
ERROR_SIGNUP_CAPTCHA_SERVICE_DOWN = 'The captcha service could not be reached'
ERROR_SIGNUP_NAME_NOT_ACCEPTABLE = 'This first_name is not acceptable'
ERROR_SIGNUP_ONLY_ONE_MTAG_ALLOWED = 'Only one managed tag can be assigned on this portal!'
ERROR_SIGNUP_MTAG_REQUIRED = 'A managed tag is required to be assigned!'
ERROR_SIGNUP_MTAG_UNKNOWN = 'The supplied managed tags do not exist: %s'
