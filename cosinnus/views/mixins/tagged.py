# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404

from taggit.models import Tag


class TaggedListMixin(object):

    def dispatch(self, request, *args, **kwargs):
        tag_slug = kwargs.get('tag', None)
        if tag_slug:
            self.tag = get_object_or_404(Tag, slug=tag_slug)
        else:
            self.tag = None
        return super(TaggedListMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TaggedListMixin, self).get_context_data(**kwargs)
        tag_ids = set()
        for o in self.object_list:
            tag_ids = tag_ids | set(o.tags.values_list('pk', flat=True).all())
        context.update({
            'tag': self.tag,
            'tags': self.model.tags.filter(pk__in=tag_ids).all().order_by('name')
        })
        return context

    def get_queryset(self):
        qs = super(TaggedListMixin, self).get_queryset()
        if self.tag:
            qs = qs.filter(tags=self.tag)
        return qs
