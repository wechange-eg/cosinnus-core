import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.utils.files import get_mitwirkomat_avatar_filename, image_thumbnail, image_thumbnail_url

logger = logging.getLogger('cosinnus')


class MitwirkomatSettings(models.Model):
    """Settings for the Mitwirk-O-Mat integration for a given group"""

    QUESTION_VALUE_NO_MATCH = '-1'
    QUESTION_VALUE_PARTIAL_MATCH = '0'
    QUESTION_VALUE_MATCH = '1'

    QUESTION_CHOICES = (
        (QUESTION_VALUE_NO_MATCH, _('Does not fit us')),
        (QUESTION_VALUE_PARTIAL_MATCH, _('Partly fits us')),
        (QUESTION_VALUE_MATCH, _('Fits us')),
    )
    QUESTION_DEFAULT = QUESTION_VALUE_PARTIAL_MATCH

    # --- system fields ---
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.SET_NULL, null=True, related_name='+'
    )
    group = models.OneToOneField(
        settings.COSINNUS_GROUP_OBJECT_MODEL,
        verbose_name=_('Group for Mitwirk-O-Mat Settings'),
        related_name='mitwirkomat_settings',
        null=False,
        on_delete=models.CASCADE,
    )

    # --- user fields ---
    is_active = models.BooleanField(
        _('Is active'),
        help_text=_('Determines if the Mitwirk-O-Mat data for this group should displayed in the API.'),
        default=False,
    )
    name = models.CharField(_('Name'), max_length=100, null=True, blank=True)
    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_(
            'Replacement description for the group description. '
            'If empty, falls back to `group.description_long` which falls back to `group.description`.'
        ),
        null=True,
        blank=True,
        max_length=750,
    )
    avatar = models.ImageField(
        _('Avatar'),
        help_text=_('Replacement avatar for the group avatar. If empty, falls back to group.avatar.'),
        null=True,
        blank=True,
        upload_to=get_mitwirkomat_avatar_filename,
        max_length=250,
    )
    # answers for the questions as defined in `COSINNUS_MITWIRKOMAT_QUESTION_LABELS`
    questions = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        verbose_name=_('User-set answers to Mitwirk-O-Mat questions'),
    )

    class Meta:
        verbose_name = _('Mitwirk-O-Mat Settings')
        verbose_name_plural = _('Mitwirk-O-Mat Settings')

    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar else self.group.avatar_url

    def get_avatar_thumbnail(self, size=(80, 80)):
        return image_thumbnail(self.avatar, size) if self.avatar else self.group.get_avatar_thumbnail(size=size)

    def get_avatar_thumbnail_url(self, size=(80, 80)):
        return image_thumbnail_url(self.avatar, size) or self.group.get_avatar_thumbnail_url(size=size)
