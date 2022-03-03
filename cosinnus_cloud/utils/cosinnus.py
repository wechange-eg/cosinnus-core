# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings

# list of `CosinnusGroup.type` choices for which the cloud folders
# should be enabled.
# default: projects and societies, not conferences
CLOUD_ENABLED_FOR_GROUP_TYPES = [0, 1]


def is_cloud_enabled_for_group(group):
    """ Checks if a CosinnusGroup should have a nextcloud folder.
        I.e., the group is of a type that should have cloud files and 
        the cloud app is active for it """
    cloud_active = bool(settings.COSINNUS_CLOUD_ENABLED)
    cloud_app_enabled = 'cosinnus_cloud' not in group.get_deactivated_apps()
    group_type_valid = group.type in CLOUD_ENABLED_FOR_GROUP_TYPES
    ret = cloud_active and cloud_app_enabled and group_type_valid
    return ret
