from django.db.models import Count, Q
from rest_framework import viewsets

from cosinnus.api.serializers.group import CosinnusProjectSerializer, CosinnusSocietySerializer
from cosinnus.api.views.mixins import (
    CosinnusFilterQuerySetMixin,
    GetForUserViewSetMixin,
    PublicCosinnusGroupFilterMixin,
    ReadOnlyOrIsAdminUser,
)
from cosinnus.conf import settings
from cosinnus.models import MEMBER_STATUS, RelatedGroups
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.utils.group import get_cosinnus_group_model

CosinnusGroup = get_cosinnus_group_model()


class ExcludeSingleMemberGroupsMixin(object):
    """Adds an additional filter that excludes groups/projects with only one member,
    for use with `CosinnusFilterQuerySetMixin`."""

    def exclude_single_member_groups(self, qs):
        qs = qs.annotate(
            count_members=Count(
                'memberships',
                filter=Q(
                    memberships__status__in=MEMBER_STATUS,
                    memberships__user__is_active=True,
                    memberships__user__cosinnus_profile__tos_accepted=True,
                )
                & ~Q(
                    memberships__user__last_login__exact=None,
                    memberships__user__email__icontains='__unverified__',
                    memberships__user__cosinnus_profile___is_guest=True,
                ),
            )
        ).filter(count_members__gt=1)
        return qs

    additional_qs_filter_func = exclude_single_member_groups


class CosinnusSocietyViewSet(
    CosinnusFilterQuerySetMixin, PublicCosinnusGroupFilterMixin, GetForUserViewSetMixin, viewsets.ModelViewSet
):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get(
        'society',
        [
            'get',
        ],
    )
    permission_classes = (ReadOnlyOrIsAdminUser,)
    queryset = CosinnusSociety.objects.all()
    serializer_class = CosinnusSocietySerializer
    lookup_field = 'slug'

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # Add related groups
        for related_slug in self.request.data.get('related', []):
            related_group = CosinnusGroup.objects.filter(slug=related_slug).first()
            if not related_group:
                continue
            RelatedGroups.objects.get_or_create(from_group=serializer.instance, to_group=related_group)
            RelatedGroups.objects.get_or_create(from_group=related_group, to_group=serializer.instance)


class CosinnusSocietyExchangeViewSet(ExcludeSingleMemberGroupsMixin, CosinnusSocietyViewSet):
    """Mixes in `ExcludeSingleMemberGroupsMixin`"""

    pass


class CosinnusProjectViewSet(CosinnusSocietyViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get(
        'project',
        [
            'get',
        ],
    )
    permission_classes = (ReadOnlyOrIsAdminUser,)
    queryset = CosinnusProject.objects.all()
    serializer_class = CosinnusProjectSerializer


class CosinnusProjectExchangeViewSet(ExcludeSingleMemberGroupsMixin, CosinnusProjectViewSet):
    """Mixes in `ExcludeSingleMemberGroupsMixin`"""

    pass
