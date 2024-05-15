# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import time
from builtins import object, str
from datetime import timedelta
from uuid import uuid1

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from requests.exceptions import HTTPError
from six.moves.urllib.parse import quote_plus

from cosinnus.models import BaseHierarchicalTaggableObjectModel
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.tagged import BaseTagObject, LikeableObjectMixin
from cosinnus.utils.permissions import check_ug_membership, filter_tagged_object_queryset_for_user
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_etherpad import cosinnus_notifications
from cosinnus_etherpad.conf import settings
from cosinnus_etherpad.managers import EtherpadManager
from cosinnus_etherpad.utils.ethercalc_client import EtherCalc as EtherCalcClient
from cosinnus_etherpad.utils.etherpad_client import EtherpadException, EtherpadLiteClient

logger = logging.getLogger('cosinnus')


def _init_etherpad_client():
    """Initialises the etherpad lite client"""
    if not hasattr(settings, 'COSINNUS_ETHERPAD_BASE_URL'):
        raise ImproperlyConfigured('You have not configured ``settings.COSINNUS_ETHERPAD_BASE_URL!``')
    return EtherpadLiteClient(
        base_url=settings.COSINNUS_ETHERPAD_BASE_URL,
        api_version='1.2.7',
        base_params={'apikey': settings.COSINNUS_ETHERPAD_API_KEY},
        verify=False,
    )


def _init_ethercalc_client():
    """Initialises the ethercalc lite client"""
    return EtherCalcClient(settings.COSINNUS_ETHERPAD_ETHERCALC_BASE_URL, verify=False)


TYPE_ETHERPAD = 0
TYPE_ETHERCALC = 1

#: Choices for :attr:`visibility`: ``(int, str)``
TYPE_CHOICES = (
    (TYPE_ETHERPAD, _('Etherpad')),
    (TYPE_ETHERCALC, _('Ethercalc')),
)


class Etherpad(BaseHierarchicalTaggableObjectModel, LikeableObjectMixin):
    """Model representing an Etherpad pad."""

    SORT_FIELDS_ALIASES = [('title', 'title')]

    PAD_MODEL_TYPE = TYPE_ETHERPAD

    pad_id = models.CharField(max_length=255, editable=True)
    description = models.TextField(_('Description'), blank=True)
    # a group mapping that corresponds to the etherpads group slug at its creation time
    # used for session creation, and works even after the etherpad group's slug has changed
    group_mapper = models.CharField(max_length=255, editable=True, null=True, blank=True)

    type = models.PositiveSmallIntegerField(
        _('Pad Type'), blank=False, default=TYPE_ETHERPAD, choices=TYPE_CHOICES, editable=False
    )

    last_accessed = models.DateTimeField(
        verbose_name=_('Last accessed'),
        help_text='This will be set to now() whenever someone with write permissions accesses the write-view for this pad.',
        editable=False,
        auto_now_add=True,
    )

    objects = EtherpadManager()

    timeline_template = 'cosinnus_etherpad/v2/dashboard/timeline_item.html'

    class Meta(BaseHierarchicalTaggableObjectModel.Meta):
        verbose_name = _('Etherpad')
        verbose_name_plural = _('Etherpads')

    def __init__(self, *args, **kwargs):
        super(Etherpad, self).__init__(*args, **kwargs)
        self.PAD_MODEL_TYPE = self.type
        # class swapping magic: if a Base-classed Etherpad really is an Ethercalc,
        # swap its class to the subclass so it gets the right methods
        self.set_pad_type(self.type)
        self.init_client()

    def set_pad_type(self, pad_type):
        """Sets this instance's pad type, and corrects its __class__ to the proper Etherpad or Ethercalc class"""
        self.type = pad_type
        if self.__class__ != TYPE_CLASSES[pad_type]:
            self.__class__ = TYPE_CLASSES[pad_type]

    def init_client(self):
        self.client = _init_etherpad_client()

    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:etherpad:pad-detail', kwargs=kwargs)

    def get_edit_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:etherpad:pad-edit', kwargs=kwargs)

    def get_delete_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:etherpad:pad-delete', kwargs=kwargs)

    def get_pad_url(self):
        if self.pk:
            pad_id = quote_plus(self.pad_id.encode('utf8'))
            base_url = self.client.base_url
            base_url = base_url[: base_url.rfind('/api')]
            return '/'.join([base_url, 'p', pad_id])
        return None

    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Etherpad, self).save(*args, **kwargs)
        if created and not self.is_container:
            # pad was created
            session_id = uuid1().int
            group_followers_except_creator_ids = [
                pk for pk in self.group.get_followed_user_ids() if pk not in [self.creator_id]
            ]
            group_followers_except_creator = get_user_model().objects.filter(id__in=group_followers_except_creator_ids)
            cosinnus_notifications.followed_group_etherpad_created.send(
                sender=self, user=self.creator, obj=self, audience=group_followers_except_creator, session_id=session_id
            )
            cosinnus_notifications.etherpad_created.send(
                sender=self,
                user=self.creator,
                obj=self,
                audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk),
                session_id=session_id,
                end_session=True,
            )

    def get_user_session_id(self, user):
        group_mapper = getattr(self, 'group_mapper', None)
        if not group_mapper:
            group_mapper = _get_group_mapping(self.group)
            self.group_mapper = group_mapper
            self.save()
        author_id = self.client.createAuthorIfNotExistsFor(authorMapper=_get_author_mapping(user))
        group_id = self.client.createGroupIfNotExistsFor(groupMapper=group_mapper)
        one_year_from_now = now() + timedelta(days=365)
        valid_until = time.mktime(one_year_from_now.timetuple())

        session_id = self.client.createSession(
            groupID=group_id['groupID'], authorID=author_id['authorID'], validUntil=str(valid_until)
        )
        return session_id['sessionID']

    @property
    def content(self):
        """Returns the content of the pad as HTML.
        @raise Exception: Thrown when the content could not be retrieved. The type of exception depends on the client used."""
        return self.client.getHTML(padID=self.pad_id)['html']

    def get_content(self):
        """Safe method to return the content of this pad. Will never throw an exception.
        @return: None if an exception occured or the pad server could not be reached.
                 ``<content>:str`` as content (at least '' for an empty pad).
        """
        try:
            return self.content or ''
        except:
            return None

    @classmethod
    def get_current(self, group, user):
        """Returns a queryset of the current upcoming events"""
        qs = Etherpad.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return qs.filter(is_container=False)

    def grant_extra_read_permissions(self, user):
        """Group members may read etherpads if they are not private"""
        is_private = False
        if self.media_tag:
            is_private = self.media_tag.visibility == BaseTagObject.VISIBILITY_USER
        return check_ug_membership(user, self.group) and not is_private

    def reinit_pad(self):
        raise ImproperlyConfigured('This method is deprecated and dangerous. Pad content may be lost!')

        old_pad_id = self.pad_id
        group_id = self.client.createGroupIfNotExistsFor(groupMapper=_get_group_mapping(self.group))

        counter = 0
        while counter < 10:
            counter += 1
            try:
                pad_id = self.client.createGroupPad(
                    groupID=group_id['groupID'], padName=self.slug + '_reinit%d' % counter
                )
                break
            except EtherpadException:
                pass

        self.pad_id = pad_id['padID']

        text = self.client.getText(padID=old_pad_id)
        self.client.setText(padID=self.pad_id, text=text['text'])

        self.save()

    def get_icon(self):
        """Returns the font-awesome icon specific to this object type"""
        return 'fa-file-text'

    def __str__(self):
        return '<Etherpad%s id: %s>' % (' Folder' if self.is_container else '', self.id or '<>')


class EtherpadSpecificManager(EtherpadManager):
    def get_queryset(self):
        return super(EtherpadSpecificManager, self).get_queryset().filter(type=TYPE_ETHERPAD)

    get_query_set = get_queryset


class EtherpadSpecific(Etherpad):
    PAD_MODEL_TYPE = TYPE_ETHERPAD

    objects = EtherpadSpecificManager()

    class Meta(object):
        proxy = True


class EtherpadNotSupportedByType(ImproperlyConfigured):
    """Thrown when a method is called on a subclass of Etherpad that is not supported by that subclass"""

    pass


class EthercalcManager(EtherpadManager):
    def get_queryset(self):
        return super(EthercalcManager, self).get_queryset().filter(type=TYPE_ETHERCALC)

    get_query_set = get_queryset


class Ethercalc(Etherpad):
    PAD_MODEL_TYPE = TYPE_ETHERCALC

    objects = EthercalcManager()

    class Meta(object):
        proxy = True
        verbose_name = _('Ethercalc')
        verbose_name_plural = _('Ethercalcs')

    def init_client(self):
        self.client = _init_ethercalc_client()

    def get_pad_url(self):
        if self.pk:
            pad_id = quote_plus(self.pad_id)
            return '/'.join([settings.COSINNUS_ETHERPAD_ETHERCALC_BASE_URL, pad_id])
        return None

    def get_user_session_id(self, user):
        raise EtherpadNotSupportedByType('Unlike Etherpad, Ethercalc does not support user sessions!')

    @property
    def content(self):
        try:
            ret = self.client.export(self.pad_id, format='html')
        except HTTPError as e:
            # the calc may not have been created on the server yet
            # (empty calcs are created automatically at first data input)
            if e.response.status_code == 404:
                ret = ''
            else:
                raise
        except Exception as e:
            logger.error('Could not display an Ethercalc because of exception "%s"' % force_str(e))
            raise
        return ret

    @classmethod
    def get_current(self, group, user):
        """Returns a queryset of the current calcs"""
        qs = Ethercalc.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return qs.filter(is_container=False)

    def reinit_pad(self):
        raise ImproperlyConfigured('This method does not work for Ethercalcs')

    def save(self, allow_type_change=False, *args, **kwargs):
        if not allow_type_change:
            self.type = TYPE_ETHERCALC
        super(Ethercalc, self).save(*args, **kwargs)

    def get_icon(self):
        """Returns the font-awesome icon specific to this object type"""
        return 'fa-table'

    def __str__(self):
        return '<Ethercalc%s id: %s>' % (' Folder' if self.is_container else '', self.id or '<>')


TYPE_CLASSES = {
    TYPE_ETHERPAD: Etherpad,
    TYPE_ETHERCALC: Ethercalc,
}


def _get_group_mapping(group):
    return 'p_%s_g_%s' % (CosinnusPortal.get_current().slug, group.slug)


def _get_author_mapping(user):
    return 'p_%s_u_%s' % (CosinnusPortal.get_current().slug, user.username)


import django

if django.VERSION[:2] < (1, 7):
    from cosinnus_etherpad import cosinnus_app

    cosinnus_app.register()
