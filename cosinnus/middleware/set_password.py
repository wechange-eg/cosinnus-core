from django.contrib.auth.views import PasswordResetView


class SetPasswordMiddleware:
    def __init__(self, get_repsonse):
        self.get_response = get_repsonse

    def __call__(self, request):
        user = request.user
        if request.user and request.user.is_authenticated:
            if not request.user.password:
                # redirect to set password view
                pass
            else:
                # redirect to requested view
                pass