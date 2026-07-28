# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from taggit.models import TaggedItem

from cosinnus.models import BaseTaggableObjectManager


class OfferManager(BaseTaggableObjectManager):
    def public(self):
        return self.get_queryset().filter(public=True, is_active=True)

    def all_active(self):
        return self.get_queryset().filter(is_active=True)

    def tags(self):
        offer_type = ContentType.objects.get(app_label='cosinnus_marketplace', model='offer')

        tag_names = []
        for ti in TaggedItem.objects.filter(content_type_id=offer_type):
            if ti.tag.name not in tag_names:
                tag_names.append(ti.tag.name)

        return tag_names

    def get_personal(self, user):
        objects = super().get_personal(user)
        # consider only active offers
        objects = objects.filter(is_active=True)
        return objects
