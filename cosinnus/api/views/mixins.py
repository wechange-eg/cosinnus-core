from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import action

from cosinnus.conf import settings
from cosinnus.models import BaseTagObject, CosinnusPortal


class PublicCosinnusGroupFilterMixin(object):
    def get_queryset(self):
        queryset = super().get_queryset()
        # filter for current portal
        queryset = queryset.filter(portal=CosinnusPortal.get_current())
        # Filter visibility
        queryset = queryset.filter(is_active=True)
        # Filter by 'publicly_visible'
        if settings.COSINNUS_GROUP_PUBLICY_VISIBLE_OPTION_SHOWN:
            # Filter by field value if the option is shown
            queryset = queryset.filter(publicly_visible=True)
        elif settings.COSINNUS_GROUP_PUBLICLY_VISIBLE_DEFAULT_VALUE is False:
            # Return empty queryset if the option is not shown and the default value is False.
            queryset = queryset.none()
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
            'true': [~Q(avatar='')],
            'false': [Q(avatar='')],
        }
    }
    # a list of additionally allowed GET params as filters, and their QS filter key mapping
    # apart from these, only filter params are allowed that are fields returned by the view's serializer class
    FILTER_KEY_MAP = {
        'tags': 'media_tag__tags__name',
        'group_id': 'group_id',
    }
    FILTER_VALUE_MAP = {'false': False, 'true': True}
    FILTER_DEFAULT_ORDER = [
        '-created',
    ]
    MANAGED_TAGS_KEY = 'managed_tags'
    # if true, filter managed tags on the group of the object, not on the object itself
    MANAGED_TAGS_FILTER_ON_GROUP = False

    # can be defined in implementing views, to additionally filter the queryset
    additional_qs_filter_func = None

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
                f'{mtag_filter_prefix}managed_tag_assignments__approved': True,
            }
            queryset = queryset.filter(**mtag_filter)
            query_params.pop(self.MANAGED_TAGS_KEY)
        # Overwrite ugly but commonly used filters
        for key, value in list(query_params.items()):
            if key in (self.pagination_class.limit_query_param, self.pagination_class.offset_query_param):
                continue
            if key in self.FILTER_CONDITION_MAP:
                VALUE_MAP = self.FILTER_CONDITION_MAP.get(key)
                if value in VALUE_MAP:
                    queryset = queryset.filter(*VALUE_MAP.get(value))
            else:
                exclude = False
                if key.startswith('exclude_'):
                    exclude = True
                    key = key[8:]
                value = self.FILTER_VALUE_MAP.get(value, value)
                if value is None:
                    continue
                # only allow filtering on whitelisted filter params and the serializer's output fields
                if key not in self.FILTER_KEY_MAP and key not in self.get_serializer_class().Meta.fields:
                    continue
                key = self.FILTER_KEY_MAP.get(key, key)
                if exclude:
                    queryset = queryset.exclude(**{key: value})
                else:
                    queryset = queryset.filter(**{key: value})

        # run additional filters for extending ViewSets, for example for exchange views
        if self.additional_qs_filter_func:
            queryset = self.additional_qs_filter_func(queryset)
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
        """Displays groups/projects that the currently logged in user is a member of."""
        queryset = self.queryset.model
        queryset = queryset.objects.get_for_user(self.request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer_class()(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
