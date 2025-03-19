from oauth2_provider.oauth2_validators import OAuth2Validator

from cosinnus.models.group import CosinnusPortal
from cosinnus.models.membership import MEMBERSHIP_ADMIN, MEMBERSHIP_MANAGER, MEMBERSHIP_MEMBER


class CustomOAuth2Validator(OAuth2Validator):
    """OAuth2Validator that extends the userinfo."""

    def get_userinfo_claims(self, request):
        """
        Populate userinfo as returned by the /o/userinfo/ endpoint.
        See https://django-oauth-toolkit.readthedocs.io/en/latest/oidc.html#adding-information-to-the-userinfo-service
        Note: Mostly a copy of the cosinnus_cloud.views.OAuthView and cosinnus.api.views.user.OAuthUserView
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
                avatar_url = portal.get_absolute_url() + avatar_url

            membership_type_map = {
                MEMBERSHIP_ADMIN: 'admins',
                MEMBERSHIP_MANAGER: 'managers',
                MEMBERSHIP_MEMBER: 'users',
            }
            group_dict = {}
            group_url_dict = {}
            for group in user.cosinnus_profile.cosinnus_groups:
                # add a {group_id --> membership type} entry for each group the user is a member of
                membership = group.memberships.filter(user=user)[0]
                membership_type = membership_type_map.get(membership.status, None)
                if membership_type:
                    group_dict.update(
                        {
                            str(group.id): membership_type,
                        }
                    )
                # add a {group_id --> group_url} entry for each group the user is a member of
                group_url_dict.update(
                    {
                        str(group.id): group.get_absolute_url(),
                    }
                )

            claims.update(
                {
                    'email': email,
                    'name': user.cosinnus_profile.get_external_full_name(),
                    'avatar': avatar_url,
                    'group': group_dict,
                    'group_urls': group_url_dict,
                }
            )
        return claims
