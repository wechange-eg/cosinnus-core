# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django.core.exceptions import PermissionDenied

from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.permissions import check_ug_membership, check_user_superuser


class RequireLoggedIn(object):
    def check_all_permissions(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied


class RequireGroupMember(RequireLoggedIn):
    group_slug_field = 'group'
    group_class = CosinnusGroup

    def check_all_permissions(self, request, *args, **kwargs):
        super(RequireGroupMember, self).check_all_permissions(request, *args, **kwargs)

        group_slug = kwargs.get(self.group_slug_field, None)
        if group_slug is None:
            raise PermissionDenied

        try:
            self.group = self.group_class.objects.get(slug=group_slug)
        except self.group_class.DoesNotExist:
            raise PermissionDenied

        user = request.user

        if not (check_user_superuser(user) or check_ug_membership(user, self.group)):
            raise PermissionDenied
