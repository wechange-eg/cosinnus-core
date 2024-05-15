import logging

from django.core.management.base import BaseCommand

from oauth2_provider.models import AccessToken, RefreshToken
from cosinnus.models.profile import get_user_profile_model, PROFILE_SETTING_ROCKET_CHAT_ID, PROFILE_SETTING_ROCKET_CHAT_USERNAME
from django.contrib.auth import get_user_model
from cosinnus.utils.user import is_user_active
from cosinnus.models.group import CosinnusPortal, CosinnusGroupMembership
from cosinnus.conf import settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



class Command(BaseCommand):
    """ Fixes any users that have PROFILE_SETTING_ROCKET_CHAT_USERNAME in their profile, but no PROFILE_SETTING_ROCKET_CHAT_ID,
        by removing the PROFILE_SETTING_ROCKET_CHAT_USERNAME.
        These users never had rocketchat accounts created. """
    
    def handle(self, *args, **options):
        if not settings.COSINNUS_ROCKET_ENABLED:
            self.stdout.write('Rocketchat is not enabled on this portal.')
            return
        
        DO_DELETE = True
        
        user_list_count = get_user_model().objects.all().count()
        affected_users = []
        for i, checking_user in enumerate(get_user_model().objects.all()):
            if i % 100 == 0:
                self.stdout.write(f'>> -------- check {i}/{user_list_count} - {checking_user.id} -----------------')
                self.stdout.flush()
            if not getattr(checking_user, 'cosinnus_profile', None) or not checking_user.cosinnus_profile.settings:
                continue
            profile = checking_user.cosinnus_profile
            if not PROFILE_SETTING_ROCKET_CHAT_USERNAME in profile.settings and not PROFILE_SETTING_ROCKET_CHAT_ID in profile.settings:
                continue
            if profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_USERNAME, None) and profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID, None):
                continue
            
            # remove pairless or empty RC attributes
            if PROFILE_SETTING_ROCKET_CHAT_USERNAME in profile.settings and not profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID, None):
                self.stdout.write(f'Fixing uid: {checking_user.id}, is_active: {checking_user.is_active}, mail: {checking_user.email}, signup {checking_user.date_joined}, lastlogin {checking_user.last_login}, rocket_chat_id {profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID, "-")}, rocket_chat_username {profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_USERNAME, "-")}')
                if DO_DELETE:
                    del profile.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME]
                    if PROFILE_SETTING_ROCKET_CHAT_ID in profile.settings:
                        del profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID]
                    # save without triggers
                    type(profile).objects.filter(pk=profile.pk).update(settings=profile.settings)
                affected_users.append(checking_user)
        
        self.stdout.write(f'>> Done: {len(affected_users)}')
        