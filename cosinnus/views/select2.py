# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404

from django_select2 import Select2View, NO_ERR_RESP
from taggit.models import Tag

from cosinnus.models.group import CosinnusGroup, CosinnusPortal
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus.utils.choices import get_user_choices
from cosinnus.utils.permissions import check_ug_membership
from cosinnus.views.mixins.select2 import RequireGroupMember, RequireLoggedIn
from cosinnus.utils.group import get_cosinnus_group_model


class GroupMembersView(RequireGroupMember, Select2View):
    
    def get_results(self, request, term, page, context):
        term = term.lower()
        start = (page - 1) * 10
        end = page * 10

        User = get_user_model()

        uids = self.group.members
        # if this is a Project, add all users of its parent Group as well
        if self.group.parent:
            uids = list(set(uids + self.group.parent.members))
            
        q = Q(id__in=uids)
        q &= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term)

        count = User.objects.exclude(is_active=False).exclude(last_login__exact=None).filter(q).count()
        if count < start:
            raise Http404
        has_more = count > end

        users = User.objects.exclude(is_active=False).exclude(last_login__exact=None).filter(q).all()[start:end]
        results = get_user_choices(users)

        return (NO_ERR_RESP, has_more, results)

group_members = GroupMembersView.as_view()



class AllMembersView(RequireLoggedIn, Select2View):
    
    def get_results(self, request, term, page, context):
        term = term.lower()
        start = (page - 1) * 10
        end = page * 10

        User = get_user_model()

        q = Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(username__icontains=term) | Q(email__icontains=term)
        user_qs = User.objects.exclude(is_active=False).exclude(last_login__exact=None).filter(id__in=CosinnusPortal.get_current().members).filter(q)
        
        count = user_qs.count()
        if count < start:
            raise Http404
        has_more = count > end

        users = user_qs.all()[start:end]
        results = get_user_choices(users)

        return (NO_ERR_RESP, has_more, results)

all_members = AllMembersView.as_view()


class TagsView(Select2View):
    
    def get_results(self, request, term, page, context):
        term = term.lower()
        start = (page - 1) * 10
        end = page * 10

        q = Q(name__icontains=term)
        count = Tag.objects.filter(q).count()
        if count < start:
            raise Http404
        has_more = count > end

        tags = list(Tag.objects.filter(q).values_list('name', 'name').all()[start:end])

        return (NO_ERR_RESP, has_more, tags)

tags_view = TagsView.as_view()



class GroupsView(Select2View):
    
    def get_results(self, request, term, page, context):
        term = term.lower()
        start = (page - 1) * 10
        end = page * 10

        q = Q(name__icontains=term)
        # add all extra lookup fields defined by swapped out group models
        for lookup_field in get_cosinnus_group_model().NAME_LOOKUP_FIELDS:
            if lookup_field != 'name':
                q = q | Q(**{lookup_field+'__icontains':term})
        qs = get_cosinnus_group_model().objects.filter(q).filter(portal_id=CosinnusPortal.get_current().id)
        if request.GET.get('except', None):
            qs = qs.exclude(id=int(request.GET.get('except')))
        # TODO: also search russian/other extension fields of name, make a good interface to generically grab those
        
        count = qs.count()
        if count < start:
            raise Http404
        has_more = count > end
        
        groups = []
        for group in qs[start:end]:
            # access group.name by its dict lookup to support translation magic
            groups.append((group.id, group['name']))
            
        return (NO_ERR_RESP, has_more, groups)

groups_view = GroupsView.as_view()


