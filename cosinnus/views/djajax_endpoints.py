# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.permissions import check_object_write_access

from djajax.views import DjajaxEndpoint


class DjajaxCosinnusEndpoint(DjajaxEndpoint):
    
    def check_write_permissions(self, obj, user, **kwargs):
        """ Permissions check if ``user`` may modify ``obj``.
            It is highly recommended to override this method!
        """
        return check_object_write_access(obj, user, **kwargs)