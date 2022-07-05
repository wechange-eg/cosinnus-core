from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import action

from cosinnus.models import CosinnusPortal, BaseTagObject


class PublicCosinnusGroupFilterMixin(object):

    def get_queryset(self):
        queryset = super().get_queryset()
        # filter for current portal
        queryset = queryset.filter(portal=CosinnusPortal.get_current())
        # Filter visibility
        queryset = queryset.filter(is_active=True)
        return queryset


class PublicTaggableObjectFilterMixin(object):

    def get_queryset(self):
        queryset = self.queryset
        # filter for current portal
        queryset = queryset.filter(group__portal=CosinnusPortal.get_current())
        # Filter visibility
        queryset = queryset.filter(group__is_active=True, media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        return queryset


class CosinnusFilterQuerySetMixin(object):
    FILTER_CONDITION_MAP = {
        'avatar': {
            'true': [~Q(avatar="")],
            'false': [Q(avatar="")],
        }
    }
    FILTER_KEY_MAP = {
        'tags': 'media_tag__tags__name',
    }
    FILTER_VALUE_MAP = {
        'false': False,
        'true': True
    }
    FILTER_DEFAULT_ORDER = ['-created', ]
    MANAGED_TAGS_KEY = 'managed_tags'
    # if true, filter managed tags on the group of the object, not on the object itself
    MANAGED_TAGS_FILTER_ON_GROUP = False

    def get_queryset(self):
        """
        Optionally filter by group
        FIXME: Use generic filters here after upgrade to django-filter==0.15.0
        """
        queryset = super().get_queryset()
        # Order
        query_params = self.request.query_params.copy()
        order_by = query_params.pop('order_by', self.FILTER_DEFAULT_ORDER)
        queryset = queryset.order_by(*order_by)
        # Managed tag filters
        if self.MANAGED_TAGS_KEY in query_params:
            managed_tags = query_params.getlist(self.MANAGED_TAGS_KEY)
            mtag_filter_prefix = 'group__' if self.MANAGED_TAGS_FILTER_ON_GROUP else ''
            mtag_filter = {
                f'{mtag_filter_prefix}managed_tag_assignments__managed_tag__slug__in': managed_tags,
                f'{mtag_filter_prefix}managed_tag_assignments__approved': True
            }
            queryset = queryset.filter(**mtag_filter)
            query_params.pop(self.MANAGED_TAGS_KEY)
        # Overwrite ugly but commonly used filters
        for key, value in list(query_params.items()):
            if key in (self.pagination_class.limit_query_param,
                       self.pagination_class.offset_query_param):
                continue
            if key in self.FILTER_CONDITION_MAP:
                VALUE_MAP = self.FILTER_CONDITION_MAP.get(key)
                if value in VALUE_MAP:
                    queryset = queryset.filter(*VALUE_MAP.get(value))
            else:
                key = self.FILTER_KEY_MAP.get(key, key)
                value = self.FILTER_VALUE_MAP.get(value, value)
                if value is None:
                    continue
                if key.startswith('exclude_'):
                    queryset = queryset.exclude(**{key[8:]: value})
                else:
                    queryset = queryset.filter(**{key: value})
        return queryset


class CosinnusPaginateMixin(object):

    def get_queryset(self):
        queryset = super().get_queryset()
        page = self.paginate_queryset(queryset)
        return page


class ReadOnlyOrIsAdminUser(permissions.IsAdminUser):
    def has_permission(self, request, view):
        return view.action in ['list', 'retrieve', 'mine'] or super().has_permission(request, view)


class GetForUserViewSetMixin(object):

    @action(detail=False, methods=['get'])
    def mine(self, request):
        queryset = self.queryset.model
        queryset = queryset.objects.get_for_user(self.request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer_class()(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)
