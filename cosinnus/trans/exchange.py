from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.utils.functions import resolve_class


class CosinnusExternalResourceTransBase:
    """A class containing all type-specific translation strings for external resources.
    Can be drop-in replaced per-portal with the setting `COSINNUS_EXTERNAL_RESOURCE_TRANS_DROPIN`.
    """

    ICON = 'fa-external-link'
    LARGE_ICON = 'images/fa-icons/large/fa-external-link.png'
    VERBOSE_NAME = _('External Resource')
    VERBOSE_NAME_PLURAL = _('External Resources')


CosinnusExternalResourceTrans = CosinnusExternalResourceTransBase
if getattr(settings, 'COSINNUS_EXTERNAL_RESOURCE_TRANS_DROPIN', None):
    CosinnusExternalResourceTrans = resolve_class(settings.COSINNUS_EXTERNAL_RESOURCE_TRANS_DROPIN)
