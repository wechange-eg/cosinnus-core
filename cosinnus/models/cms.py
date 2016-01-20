# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings


@python_2_unicode_compatible
class CosinnusMicropage(models.Model):
    
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='micropages',
                null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(_('Title'), max_length=100)
    text = models.TextField(verbose_name=_('Text'), blank=True)
    last_edited = models.DateTimeField(verbose_name=_('Last edited'), editable=False,
        auto_now=True)
    last_edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Last edited by'),
        editable=False, on_delete=models.PROTECT, null=True, related_name='%(app_label)s_%(class)s_set')
    
    class Meta:
        app_label = 'cosinnus'
        verbose_name = _('Cosinnus CMS Micropage')
        verbose_name_plural = _('Cosinnus Micropages')
        
    def __str__(self):
        return "<CosinnusMicropage '%s'>" % self.title
    
    def __repr__(self):
        return "<CosinnusMicropage {0} (ID: {1})>".format(self.title, self.pk)
    
    def save(self, *args, **kwargs):
        self.last_edited = now()
        super(CosinnusMicropage, self).save(*args, **kwargs)
