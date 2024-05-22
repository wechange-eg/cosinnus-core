from rest_framework.views import exception_handler


def cosinnus_error_code_exception_handler(exc, context):
    """Pass return 'error_code' and 'error_message' along with the response
    if the APIException or ValidationError carried a cosinnus error code
    (see `CosinnusErrorCodeAPIExceptionMixin`)"""

    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # TODO: we might do our custom exception handling here if we want to return error codes differently.
    # if the exception has an `error_obj`, we pass return 'error_code' and 'error_message'
    # along with the response (see `CosinnusErrorCodeAPIExceptionMixin`)

    return response
