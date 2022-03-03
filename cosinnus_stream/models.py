# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
import datetime

from django.urls import reverse
from django.db import models as django_models
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from cosinnus.conf import settings
from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus_stream.mixins import StreamManagerMixin
from django.core.cache import cache
from cosinnus.models.group import CosinnusPortal
from django.db.models.signals import post_save
from django.utils.encoding import force_text
from django.core.validators import validate_comma_separated_integer_list

import logging
logger = logging.getLogger('cosinnus')

USER_STREAM_SHORT_CACHE_KEY = 'cosinnus/stream/portals_%s/user/%d/short_stream'

class StreamManager(django_models.Manager):
    
    def my_stream_unread_count(self, user):
        if not user.is_authenticated:
            return 0
        try:
            stream = self.get_my_stream_for_user(user, portals=str(CosinnusPortal.get_current().id))
        except Exception as e:
            extra = {'exception': force_text(e), 'user': user}
            logger.error('Error when trying to get MyStream for stream unread count. Exception in extra.', extra=extra)
            return 0
        return stream.unread_count()
    
    def get_my_stream_for_user(self, user, portals=""):
        # 10 second user based cache for stream
        stream = cache.get(USER_STREAM_SHORT_CACHE_KEY % (portals, user.id))
        if stream is None:
            # try to find the user's MyStream, if not existing, create it
            try:
                stream = self.model._default_manager.get(creator=user, is_my_stream__exact=True, portals__exact=portals)
            except self.model.DoesNotExist:
                portal_str = portals.replace(',','_')
                stream = self.model._default_manager.create(creator=user, 
                            title="_my_stream_%s" % portal_str, slug="_my_stream_%s" % portal_str,
                            is_my_stream=True, portals=portals)
            stream.update_cache(user)
        return stream


class Stream(StreamManagerMixin, BaseTaggableObjectModel):
    
    class Meta(BaseTaggableObjectModel.Meta):
        verbose_name = _('Stream')
        verbose_name_plural = _('Streams')
        ordering = ['created']
        unique_together = (('creator', 'slug'),)
    
    models = django_models.CharField(_('Models'), blank=True, null=True, max_length=255)
    is_my_stream = django_models.BooleanField(default=False)
    portals = django_models.CharField(_('Portal IDs'), 
       blank=True, null=False, max_length=255, default="", validators=[validate_comma_separated_integer_list])
    last_seen = django_models.DateTimeField(_('Last seen'), default=None, blank=True, null=True)
    
    is_special = django_models.BooleanField(_('Special Stream'), default=False)
    special_groups = django_models.CharField(_('Special Group IDs'), 
       blank=True, null=False, max_length=255, default="", validators=[validate_comma_separated_integer_list])
    
    objects = StreamManager()
    
    @property
    def portal_list(self):
        return [int(portal_str.strip()) for portal_str in [portal for portal in self.portals.split(',') if portal]]
    
    def set_last_seen(self, when=None):
        """ Set the last seen datetime for this stream. 
            Sets the datetime to now() if no argument is passed.
        """
        self.last_seen = when or now()
        if self.pk:
            self.save()
            # re-calculate unread count
            self.unread_count(force=True)
    
    @property
    def last_seen_safe(self):
        last_seen = self.last_seen or datetime.datetime(1990, 1, 1)
        return last_seen
    
    def get_absolute_url(self):
        kwargs = {'slug': self.slug}
        return reverse('cosinnus:stream', kwargs=kwargs)
    
    def update_cache(self, user):
        try:
            cache.set(USER_STREAM_SHORT_CACHE_KEY % (self.portals, user.id if user.is_authenticated else 0), \
                      self, settings.COSINNUS_STREAM_SHORT_CACHE_TIMEOUT)
        except Exception as e:
            # sometimes we cannot pickle the deep cache and it throws errors, we don't want to let this bubble up
            logger.warning('Could not save the user stream into the cache because of an exception! (in extra)', extra={'exception': force_text(e)})
            
    
    # def unread_count() is in the StreamManagerMixin!
    
""" We swap the unique together field for group for creator. Group is no longer required, but creator is. """
Stream._meta.get_field('group').blank = True
Stream._meta.get_field('group').null = True
Stream._meta.get_field('creator').blank = False
Stream._meta.get_field('creator').null = False
Stream._meta.unique_together = (('creator', 'slug'),)

    
def create_special_streams_profile(sender, instance, created, **kwargs):
    """
    Creates hardcoded special streams for a new user, taken from settings.
    """
    if created and getattr(settings, 'COSINNUS_STREAM_SPECIAL_STREAMS'): 
        user = instance
        for special_stream in settings.COSINNUS_STREAM_SPECIAL_STREAMS:
            # create all special hardcoded streams
            Stream.objects.get_or_create(
                 creator=user, 
                 is_special=True, 
                 special_groups=','.join([force_text(gid) for gid in special_stream['group_ids']]),
                 defaults={
                    'models': special_stream['app_models'],
                    'title': special_stream['title'],
                 },
            )

post_save.connect(create_special_streams_profile, sender=settings.AUTH_USER_MODEL,
    dispatch_uid='cosinnus_user_profile_post_save_streams')


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_stream import cosinnus_app
    cosinnus_app.register()
