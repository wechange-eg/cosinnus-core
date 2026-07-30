# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from taggit.models import TaggedItem

from cosinnus.models import BaseTaggableObjectManager


class PollManager(BaseTaggableObjectManager):
    def public(self):
        # Django 1.5: get_query_set, 1.7: get_queryset
        qs = getattr(self, 'get_queryset', self.get_query_set)()
        return qs.filter(public=True, state=self.model.STATE_SCHEDULED)

    def tags(self):
        poll_type = ContentType.objects.get(app_label='cosinnus_poll', model='poll')

        tag_names = []
        for ti in TaggedItem.objects.filter(content_type_id=poll_type):
            if ti.tag.name not in tag_names:
                tag_names.append(ti.tag.name)

        return tag_names

    def get_personal_items(self, user):
        queryset = super().get_personal_items(user)
        queryset = queryset.exclude(group__deactivated_apps__contains='cosinnus_poll')
        return queryset

    def get_personal_open_polls(self, user):
        """Return open polls where the user has not voted yet."""
        queryset = self.get_personal_items(user)
        queryset = queryset.filter(state=self.model.STATE_VOTING_OPEN)
        queryset = queryset.exclude(options__votes__voter__id=user.pk)
        return queryset
