# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.functional import cached_property
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class BaseUserProfile(models.Model):
    """
    This is a base user profile used within cosinnus. To use it, create your
    own model inheriting from this model and register a ``post_save`` signal on
    the user model and call ``.get_profile()`` on a user instance.

    .. code-block:: python

        class UserProfile(BaseUserProfile):
            pass


        @receiver(post_save, sender=get_user_model())
        def create_user_profile(sender, instance, created, **kwargs):
            if created:
                UserProfile.objects.get_or_create(user=instance)

    .. node::

        If you are using Django >= 1.5 and are able to use the custom user
        model, this is preferred!

    .. warning::

        This feature is deprecated in Django 1.5 and will be removed in 1.7!

    .. todo::

        Replace with custom user object when Django CMS and other 3rd-party
        apps have added support for them
    """
    user = models.OneToOneField(get_user_model(), editable=False)

    SKIP_FIELDS = ('id', 'user',)

    class Meta:
        abstract = True

    def __str__(self):
        return self.user.get_username()

    def save(self, *args, **kwargs):
        try:
            existing = self._default_manager.get(user=self.user)
            # workaround for http://goo.gl/4I8Ok
            self.id = existing.id  # force update instead of insert
        except ObjectDoesNotExist:
            pass
        super(BaseUserProfile, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('cosinnus:profile-detail')

    @cached_property
    def get_optional_fields(self):
        """
        Iterates over all fields defiend in the user profile and returns a list
        of dicts with the keys ``name`` and ``value``.

        The list will only contain those fields not listed in ``SKIP_FIELDS``.
        """
        all_fields = self._meta.get_all_field_names()
        optional_fields = []
        for name in all_fields:
            if name in self.SKIP_FIELDS:
                continue
            value = getattr(self, name)
            if value:
                field = self._meta.get_field_by_name(name)[0]
                optional_fields.append({
                    'name': field.verbose_name,
                    'value': value,
                })
        return optional_fields
