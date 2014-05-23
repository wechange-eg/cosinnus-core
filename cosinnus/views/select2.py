# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404

from django_select2 import Select2View, NO_ERR_RESP

from cosinnus.models.group import CosinnusGroup
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus.utils.choices import get_user_choices
from cosinnus.utils.permissions import check_ug_membership
from cosinnus.views.mixins.select2 import RequireGroupMember


class GroupMembersView(RequireGroupMember, Select2View):
    
    def get_results(self, request, term, page, context):
        term = term.lower()
        start = (page - 1) * 10
        end = page * 10

        User = get_user_model()

        uids = self.group.members
        q = Q(id__in=uids)
        q &= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(username__icontains=term)

        count = User.objects.filter(q).count()
        if count < start:
            raise Http404
        has_more = count > end

        users = User.objects.filter(q).all()[start:end]
        results = get_user_choices(users)

        return (NO_ERR_RESP, has_more, results)

group_members = GroupMembersView.as_view()
