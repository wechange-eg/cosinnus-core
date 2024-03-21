from django.utils.encoding import force_str

from cosinnus.conf import settings


def get_obfuscated_settings_strings():
    """ Returns all settings values as string with obfuscated passwords. """
    obfuscated_settings = {}
    KEY_BLACKLIST = ['COSINNUS_CLOUD_NEXTCLOUD_AUTH' ,]
    for key in dir(settings):
        val = force_str(getattr(settings, key))
        # obfuscate passwords. for long ones, show the first few chars
        if 'password' in key.lower() or 'password' in val.lower() or \
                'secret' in key.lower() or 'secret' in val.lower() or \
                'key' in key.lower() or 'key' in val.lower() or key in KEY_BLACKLIST:
            if val.strip() and val.strip() not in ('None', 'null', '0', '[]', '{}'):
                val = str(val)
                val = (len(val) > 3 and val[:3] or '') + '***'
        obfuscated_settings[key] = val
    return obfuscated_settings
