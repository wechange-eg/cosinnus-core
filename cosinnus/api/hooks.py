import requests
from django.conf import settings
from django.dispatch import receiver

from cosinnus.api.serializers.user import UserCreateUpdateSerializer
from cosinnus.core import signals

HOOKS = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('hooks', {})

if HOOKS.get('user.activated'):

    @receiver(signals.user_activated)
    def user_activated(sender, user, **kwargs):
        data = {'signal': 'user.activated'}
        data.update(UserCreateUpdateSerializer(instance=user).data)
        for url in HOOKS.get('user.activated'):
            requests.post(url, json=data)


if HOOKS.get('user.deactivated'):

    @receiver(signals.user_deactivated)
    def user_deactivated(sender, user, **kwargs):
        data = {'signal': 'user.deactivated'}
        data.update(UserCreateUpdateSerializer(instance=user).data)
        for url in HOOKS.get('user.deactivated'):
            requests.post(url, json=data)
