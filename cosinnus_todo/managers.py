# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db import models

from taggit.models import TaggedItem


class TodoEntryQuerySet(models.query.QuerySet):

    def tag_names(self):
        ctype = ContentType.objects.get(app_label="cosinnus_todo", model="todoentry")
        clone = self._clone().order_by().values_list('id', flat=True)
        tag_names = TaggedItem.objects.filter(content_type=ctype,
                                              object_id__in=clone) \
                                      .select_related('tag') \
                                      .values_list('tag__name', flat=True) \
                                      .distinct()
        return tag_names


class TodoEntryManager(models.Manager):

    use_for_related_fields = True

    def get_queryset(self):
        return TodoEntryQuerySet(self.model, using=self._db)

    get_query_set = get_queryset

    def tag_names(self):
        return self.get_queryset().tag_names()
