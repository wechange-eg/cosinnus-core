# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.models.tagged import BaseTaggableObjectReflection
from cosinnus.conf import settings
from django.contrib.contenttypes.models import ContentType


class ReflectedObjectSelectMixin(object):
    """
    Mix this into your DetailView for BaseTaggableObject and add the template select modal
    so users will be able to pick projects/groups to reflect the DetailView.object into.
    """
    
    def get_reflect_data(self, request, group, obj):
        # if this is a group or the Forum, we can select this event to be reflected into other groups        
        reflect_is_forum = group.slug == getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        reflectable_groups = {}
        reflecting_group_ids = []
        may_reflect = request.user.is_authenticated() and \
                    ((group.type == group.TYPE_SOCIETY) or reflect_is_forum)
        if may_reflect:
            # find all groups the user can reflect into (for the forum: all of theirs, for other groups, the subprojects)
            if reflect_is_forum:
                target_groups = get_cosinnus_group_model().objects.get_for_user(request.user)
            else:
                target_groups = group.get_children() 
            target_groups = sorted(target_groups, key=lambda sortgroup: sortgroup.name.lower())
            # find already-reflecting groups for this user
            reflecting_group_ids = BaseTaggableObjectReflection.get_group_ids_for_object(obj)
            reflectable_groups = [(target_group, target_group.id in reflecting_group_ids) for target_group in target_groups if target_group != group]
        
        ct = ContentType.objects.get_for_model(obj._meta.model)
        return {
            'may_reflect': may_reflect,
            'reflectable_groups': reflectable_groups,
            'reflecting_group_ids': reflecting_group_ids,
            'reflect_is_forum': reflect_is_forum,
            'reflecting_object_id': obj.id,
            'reflecting_object_content_type': '%s.%s' % (ct.app_label, ct.model),
        }
    
    def get_context_data(self, **kwargs):
        context = super(ReflectedObjectSelectMixin, self).get_context_data(**kwargs)
        context.update(self.get_reflect_data(self.request, self.group, self.object))
        return context
    
    