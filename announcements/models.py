from django.db import models
from django.utils.translation import ugettext_lazy as _, get_language

from .managers import AnnouncementManager
from django.core.exceptions import FieldDoesNotExist


class Announcement(models.Model):

    LEVEL_DEBUG = 'debug'
    LEVEL_INFO = 'info'
    LEVEL_SUCCESS = 'success'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR = 'error'
    LEVEL_CHOICES = (
        (LEVEL_DEBUG, _('Debug')),
        (LEVEL_INFO, _('Info')),
        (LEVEL_SUCCESS, _('Success')),
        (LEVEL_WARNING, _('Warning')),
        (LEVEL_ERROR, _('Error')),
    )

    is_active = models.BooleanField(_('Is active'))
    level = models.CharField('Level', max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    
    text = models.TextField('Text', help_text='Default text. Markdown for styling is enabled!')

    text_de = models.TextField('Text (DE only)', blank=True, null=True, help_text='Markdown for styling is enabled!')
    text_en = models.TextField('Text (EN only)', blank=True, null=True, help_text='Markdown for styling is enabled!')
    text_ru = models.TextField('Text (RU only)', blank=True, null=True, help_text='Markdown for styling is enabled!')
    text_uk = models.TextField('Text (UK only)', blank=True, null=True, help_text='Markdown for styling is enabled!')
    text_pl = models.TextField('Text (PL only)', blank=True, null=True, help_text='Markdown for styling is enabled!')
    text_fr = models.TextField('Text (FR only)', blank=True, null=True, help_text='Markdown for styling is enabled!')

    objects = AnnouncementManager()

    class Meta:
        verbose_name = _('Announcement')
        verbose_name_plural = _('Announcements')
    
    def _has_field(self, name):
        try:
            self._meta.get_field(name)
            return True
        except FieldDoesNotExist:
            return False
    
    def _get_translated_field(self, key):
        value = None
        lang = get_language()
        if lang and self._has_field(key) and self._has_field('%s_%s' % (key, lang)):
            value = getattr(self, '%s_%s' % (key, lang), None)
        if value is None or value == '':
            value = getattr(self, key)
        return value

    @property
    def translated_text(self):
        return self._get_translated_field('text')
    
