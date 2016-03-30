# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings


@python_2_unicode_compatible
class WidgetConfig(models.Model):

    TYPE_DASHBOARD = 1
    TYPE_MICROSITE = 2

    TYPE_CHOICES = (
        (TYPE_DASHBOARD, _('Dashboard')),
        (TYPE_MICROSITE, _('Microsite')),
    )
    
    app_name = models.CharField(_('Application name'), max_length=20)
    widget_name = models.CharField(_('Widget name'), max_length=20)
    type = models.PositiveIntegerField(_('Widget Type'),
        choices=TYPE_CHOICES, default=TYPE_DASHBOARD,
        editable=False, null=False, blank=False
    )
    sort_field = models.CharField(_('Sort field'), max_length=20, null=False, blank=False, default="999")
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        app_label = 'cosinnus'
        # ordering = ('position',)
        verbose_name = _('Widget configuration')
        verbose_name_plural = _('Widget configurations')

    def __str__(self):
        return "{0} - {1} - {2}".format(
            self.app_name,
            self.widget_name,
            "group %s" % self.group if self.group else "user %s" % self.user
        )

    def save(self, *args, **kwargs):
        if (self.group is None) ^ (self.user is None):
            super(WidgetConfig, self).save(*args, **kwargs)
            return
        raise ValidationError(_('Either team or user must be defined.'))

    def __getitem__(self, key):
        try:
            ci = self.items.get(config_key=key)
            return ci.config_value
        except WidgetConfigItem.DoesNotExist:
            raise KeyError('No config option for %s found' % key)
    
    get_default=object()
    def get(self, key, default=get_default):
        try:
            return self[key]
        except KeyError, err:
            if default == self.get_default:
                raise err
            return default
    
    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            try:
                ci = self.items.get(config_key=key)
                ci.config_value = value
            except WidgetConfigItem.DoesNotExist:
                ci = WidgetConfigItem(config=self, config_key=key, config_value=value)
            ci.save()
            
    def __delitem__(self, key):
        try:
            self.items.get(config_key=key).delete()
        except WidgetConfigItem.DoesNotExist:
            raise KeyError('No config option for %s found' % key)
    

    def __iter__(self):
        for item in self.items.values_list('config_key', 'config_value'):
            yield item
    

@python_2_unicode_compatible
class WidgetConfigItem(models.Model):

    config = models.ForeignKey(WidgetConfig, on_delete=models.CASCADE, related_name='items')
    config_key = models.CharField(_('key'), max_length=20, db_index=True)
    config_value = models.TextField(_('value'), default='')  # VARCHAR and TEXT don't mattern in PostgreSQL

    class Meta:
        app_label = 'cosinnus'
        unique_together = ('config', 'config_key')
        verbose_name = _('Widget configuration item')
        verbose_name_plural = _('Widget configuration items')

    def __str__(self):
        return "{0}: {1}".format(self.config_key, self.config_value)
