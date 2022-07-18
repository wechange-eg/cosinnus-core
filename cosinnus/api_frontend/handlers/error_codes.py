# add here all error codes as they will be used in the frontend translation files.
# format: ERROR_NAME = (int:error_code, str:error_message
#     error_code: an int code for errors. the thousand digits are used as a category, the single digits as error code counter
#             for example: any code in 1*** is login-related
#     error_message: string that is only used as a display in the API and never shown to the user

ERROR_LOGIN_USER_DISABLED = "User is disabled"
ERROR_LOGIN_INCORRECT_CREDENTIALS = "Incorrect email or password"

ERROR_SIGNUP_EMAIL_IN_USE = "Email is already in use"
ERROR_SIGNUP_CAPTCHA_INVALID = "The captcha was not filled or was invalid"
ERROR_SIGNUP_CAPTCHA_SERVICE_DOWN = "The captcha service could not be reached"
ERROR_SIGNUP_NAME_NOT_ACCEPTABLE = "This first_name is not acceptable"

