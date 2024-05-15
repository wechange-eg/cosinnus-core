from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class CosinnusOauthClientAccount(ProviderAccount):
    pass


class CosinnusOauthClientProvider(OAuth2Provider):
    id = 'wechange'
    name = 'Wechange'
    account_class = CosinnusOauthClientAccount

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
        )

    def get_default_scope(self):
        scope = ['read']
        return scope


provider_classes = [CosinnusOauthClientProvider]
