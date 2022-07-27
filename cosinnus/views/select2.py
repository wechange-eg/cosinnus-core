# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import Http404

from django_select2 import Select2View, NO_ERR_RESP
from taggit.models import Tag

from cosinnus.models.group import CosinnusPortal
from cosinnus.views.mixins.select2 import RequireGroupMember, RequireLoggedIn
from cosinnus.utils.group import get_cosinnus_group_model, prioritize_suggestions_output
from cosinnus.utils.user import filter_active_users,\
    get_user_query_filter_for_search_terms, get_user_select2_pills
from cosinnus.views.user import UserSelect2View
from django.core.exceptions import PermissionDenied
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment
from cosinnus.conf import settings
from cosinnus.utils.permissions import check_user_superuser


class GroupMembersView(RequireGroupMember, Select2View):
    
    def get_results(self, request, term, page, context):
        term = term.lower()
        start = (page - 1) * 10
        end = page * 10

        User = get_user_model()

        uids = self.group.members
        
        # if this is a Project, add all users of its parent Group as well
        # (disabled for now as it leads to a lot of confusion)
        # if self.group.parent:
        #    uids = list(set(uids + self.group.parent.members))
        
        terms = term.strip().lower().split(' ')
        q = get_user_query_filter_for_search_terms(terms)
        
        user_qs = filter_active_users(User.objects.filter(id__in=uids).filter(q))

        user_qs = prioritize_suggestions_output(request, user_qs)
        
        count = user_qs.count()
        if count < start:
            raise Http404
        has_more = count > end

        users = user_qs.all()[start:end]
        #results = get_user_choices(users)
        results = get_user_select2_pills(users)

        return (NO_ERR_RESP, has_more, results)


class AllMembersView(RequireLoggedIn, Select2View):
    
    def filter_user_qs(self, user_qs, terms):
        q = get_user_query_filter_for_search_terms(terms)
        user_qs = filter_active_users(user_qs.filter(id__in=CosinnusPortal.get_current().members).filter(q))
        return user_qs
    
    def get_results(self, request, term, page, context):
        start = (page - 1) * 10
        end = page * 10

        User = get_user_model()
        
        terms = term.strip().lower().split(' ')
        
        user_qs = User.objects.all()
        user_qs = self.filter_user_qs(user_qs, terms)
        
        count = user_qs.count()
        if count < start:
            raise Http404
        has_more = count > end

        users = user_qs.all()[start:end]
        #results = get_user_choices(users)
        results = get_user_select2_pills(users)

        return (NO_ERR_RESP, has_more, results)


class ManagedTagsMembersView(AllMembersView):
    
    managed_tag_slug = None
    
    def dispatch(self, request, *args, **kwargs):
        self.managed_tag_slug = kwargs.pop('tag_slug', None)
        return super(ManagedTagsMembersView, self).dispatch(request, *args, **kwargs)
    
    def filter_user_qs(self, user_qs, terms):
        user_qs = super(ManagedTagsMembersView, self).filter_user_qs(user_qs, terms)
        if self.managed_tag_slug:
            profile_assignments_qs = CosinnusManagedTagAssignment.objects.get_for_model(get_user_profile_model())
            assigned_profile_ids = profile_assignments_qs.filter(managed_tag__slug=self.managed_tag_slug).values_list('object_id', flat=True)
            user_qs = user_qs.filter(cosinnus_profile__id__in=assigned_profile_ids)
        return user_qs


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


class DynamicFreetextChoicesView(Select2View):
    
    field_name = None
    
    def dispatch(self, request, *args, **kwargs):
        if 'field_name' in kwargs:
            self.field_name = kwargs.pop('field_name')
            return super(DynamicFreetextChoicesView, self).dispatch(request, *args, **kwargs)
    
    def check_all_permissions(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied('Only authenticated users have access to this endpoint')
    
    def get_results(self, request, term, page, context):
        term = term.lower()
        start = (page - 1) * 10
        end = page * 10
        
        filt = Q(**{f'dynamic_fields__{self.field_name}__icontains': term})
        qs = get_user_profile_model().objects.all().filter(filt)
        
        count = qs.count()
        if count < start:
            raise Http404
        has_more = count > end
        
        all_values = qs.values_list(f'dynamic_fields__{self.field_name}', flat=True).distinct()
        # flatten values as some returned values might be items, and some might be lists
        flat_values = []
        for val in all_values:
            flat_values += val if isinstance(val, list) else [val]
        # return only matched values
        flat_values = list(set(flat_values))
        matches = [item for item in flat_values if item and term in item.lower()]
        text_choices = [(match, match) for match in matches[start:end]]
        return (NO_ERR_RESP, has_more, text_choices)


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
        
        qs = get_cosinnus_group_model().objects.filter(q).filter(portal_id=CosinnusPortal.get_current().id, is_active=True)

        # non-superusers may only select groups they are in
        if not check_user_superuser(request.user):
            user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(request.user)
            qs = qs.filter(id__in=user_group_ids)
        
        if request.GET.get('except', None):
            qs = qs.exclude(id=int(request.GET.get('except')))

        # TODO: also search russian/other extension fields of name, make a good interface to generically grab those
        
        count = qs.count()
        if count < start:
            raise Http404
        has_more = count > end
        
        groups = []
        for group in qs[start:end]:
            # do/do not return the forum group
            #if group.slug == getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None):
            #    continue
            # access group.name by its dict lookup to support translation magic
            groups.append((group.id, group['name']))
            
        return (NO_ERR_RESP, has_more, groups)


group_members = GroupMembersView.as_view()
all_members = AllMembersView.as_view()
managed_tagged_members = ManagedTagsMembersView.as_view()
tags_view = TagsView.as_view()
dynamic_freetext_choices_view = DynamicFreetextChoicesView.as_view()
groups_view = GroupsView.as_view()
