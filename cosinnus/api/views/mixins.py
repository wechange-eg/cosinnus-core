from django.db.models import Q

from cosinnus.models import CosinnusPortal, BaseTagObject


class PublicCosinnusGroupFilterMixin(object):

    def get_queryset(self):
        queryset = self.queryset
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


class CosinnusFilterQuerySetMixin:
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
            queryset = queryset.filter(managed_tag_assignments__managed_tag__slug__in=managed_tags,
                                       managed_tag_assignments__approved=True)
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