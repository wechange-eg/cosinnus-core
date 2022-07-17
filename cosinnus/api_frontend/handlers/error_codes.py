# add here all error codes as they will be used in the frontend translation files.
# format: ERROR_NAME = (int:error_code, str:error_message)
#     error_code: an int code for errors. the thousand digits are used as a category, the single digits as error code counter
#             for example: any code in 1*** is login-related
#     error_message: string that is only used as a display in the API and never shown to the user

ERROR_LOGIN_USER_DISABLED = (1001, "User is disabled")
ERROR_LOGIN_INCORRECT_CREDENTIALS = (1002, "Incorrect email or password")


