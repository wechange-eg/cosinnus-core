from oauth2_provider.oauth2_validators import OAuth2Validator

from cosinnus.models.group import CosinnusGroup, CosinnusPortal


class CustomOAuth2Validator(OAuth2Validator):
    """OAuth2Validator that extends the userinfo."""

    def get_userinfo_claims(self, request):
        """
        Populate userinfo as returned by the /o/userinfo/ endpoint.
        See https://django-oauth-toolkit.readthedocs.io/en/latest/oidc.html#adding-information-to-the-userinfo-service
        Note: Mostly a copy of the cosinnus_cloud.views.OAuthView
        """
        claims = super().get_userinfo_claims(request)
        user = request.user
        if not user.is_guest:
            portal = CosinnusPortal.get_current()
            if portal.email_needs_verification and not user.cosinnus_profile.email_verified:
                email = ''
            else:
                email = user.email.lower()

            avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ''
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)

            claims.update(
                {
                    'email': email,
                    'name': user.cosinnus_profile.get_external_full_name(),
                    'avatar': avatar_url,
                    'groups': [group.name for group in CosinnusGroup.objects.get_for_user(user)],
                }
            )
        return claims
