from rest_framework import serializers


# deprecated/unused
class CosinnusValidationError(serializers.ValidationError):
    """Deprecated:
    A validation error that builds its error messages from a cosinnus error code tuple
    from `cosinnus.api_frontend.handlers.error_objs`.

    Sadly we cannot attach the error code to either the ValidationError itself
    or even the ErrorDetails as during rest framework exception handling,
    both of these objects are stripped and built anew instead of being re-used
    and passed through."""

    def __init__(self, error_obj, **kwargs):
        """@param error_obj: a tuple from `cosinnus.api_frontend.handlers.error_objs`."""
        super().__init__(f'{error_obj[0]}: {error_obj[1]}', **kwargs)
