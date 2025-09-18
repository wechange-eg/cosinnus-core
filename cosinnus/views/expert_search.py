from collections import defaultdict

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from cosinnus.conf import settings
from cosinnus.dynamic_fields import dynamic_fields
from cosinnus.models.profile import get_user_profile_model
from cosinnus.views.map_api import map_search_endpoint
from cosinnus.views.mixins.group import EndlessPaginationMixin, RequireLoggedInMixin


class CosinnusExpertProfileListView(RequireLoggedInMixin, EndlessPaginationMixin, ListView):
    model = get_user_profile_model()
    template_name = 'cosinnus/expert_search/user_list.html'
    items_template = 'cosinnus/expert_search/user_list_items.html'
    paginator_class = Paginator
    title = _('Search for Experts')
    description = _('Here you can find experts who exactly fit your criteria.')

    # default filter type, available values "and"/"or".
    default_filter_type = 'and'
    # Show filter type selection  ("or", "and")
    filter_type_select_enabled = False

    # List of dynamic fields used for filtering
    FILTERS = []
    # Overwrite filter labels, the dynamic field label is used by default
    FILTER_LABEL_OVERWRITES = {}

    @cached_property
    def users(self):
        return super().get_queryset()

    def get_queryset(self):
        qs = self.get_data_from_api_endpoint(self.request)
        qs = self.apply_filters(qs)
        return qs

    def get_managed_tag(self):
        return None

    def get_current_filter_list(self, filter):
        return self.request.GET.getlist(filter)

    def get_current_filters(self, filter):
        return self.request.GET.get(filter)

    def get_filter_options(self, name):
        dynamic_field = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS[name]
        if dynamic_field.type == dynamic_fields.DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT:
            choices = dynamic_field.choices
        else:
            # extend for other types of dynamic field choices, e.g. admin defined choices
            raise NotImplementedError()
        return choices

    def get_filter_label(self, name):
        if name in self.FILTER_LABEL_OVERWRITES:
            return self.FILTER_LABEL_OVERWRITES[name]
        dynamic_field = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS[name]
        return dynamic_field.label

    def get_filters(self):
        filters = []
        for name in self.FILTERS:
            filters.append(
                {
                    'name': name,
                    'label': self.get_filter_label(name),
                    'options': self.get_filter_options(name),
                    'current': self.get_current_filter_list(name),
                }
            )
        return filters

    def get_active_filters(self):
        filters = defaultdict(list)
        for filter_name in self.FILTERS:
            # TODO: consider text filter
            filter_values = self.get_current_filter_list(filter_name)
            for value in filter_values:
                query_paramter = 'dynamic_fields__{}__contains'.format(filter_name)
                filters[query_paramter].append(value)
        return filters

    def get_filter_type(self):
        return self.get_current_filters('filter_type') or self.default_filter_type

    def apply_filters(self, queryset):
        filter_type = self.get_filter_type()
        active_filters = self.get_active_filters()
        if filter_type == 'and' and active_filters:
            q_objects = Q()
            for key, value in active_filters.items():
                for entry in value:
                    filter = {}
                    filter[key] = entry
                    q_objects &= Q(**filter)
            return queryset.filter(q_objects)
        elif filter_type == 'or':
            q_objects = Q()
            for key, value in active_filters.items():
                for entry in value:
                    filter = {}
                    filter[key] = entry
                q_objects |= Q(**filter)
            if not self.get_current_filters('q'):
                return queryset.filter(q_objects)
            else:
                mentors_query_string = queryset
                get_params = self.request.GET
                user = self.request.user
                request = HttpRequest()
                request.method = 'GET'
                request.user = user
                for key, value in get_params.items():
                    if not key == 'q':
                        request.GET[key] = value
                all_mentors = self.get_data_from_api_endpoint(request)
                if len(active_filters) > 0:
                    mentors_query_string = mentors_query_string | all_mentors.filter(q_objects)
                return mentors_query_string
        return queryset

    def get_data_from_api_endpoint(self, request):
        if 'page' in request.GET:
            get_params = request.GET
            user = request.user
            request = HttpRequest()
            request.method = 'GET'
            request.user = user
            for key, value in get_params.items():
                if not key == 'page':
                    request.GET[key] = value
        # add managed tag param
        request.GET._mutable = True
        if self.get_managed_tag():
            request.GET['managed_tags'] = str(self.get_managed_tag().id)
        request.GET['people'] = 'true'
        request.GET['events'] = 'false'
        request.GET['projects'] = 'false'
        request.GET['groups'] = 'false'
        request.GET['ideas'] = 'false'
        request.GET['conferences'] = 'false'
        request.GET['cloudfiles'] = 'false'
        # we do our own pagination in this view, so set page limit to much
        request.GET['limit'] = str(self.users.count())
        request.GET['ignore_location'] = 'true'
        result = map_search_endpoint(request, skip_limit_backend=True)
        result_dict = result.data.get('results')
        slugs = [entry['slug'] for entry in result_dict]
        return self.users.filter(user__username__in=slugs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = self.get_filters()
        context.update(
            {
                'title': self.title,
                'description': self.description,
                'items_template': self.items_template,
                'filters': filters,
                'current_search': self.get_current_filters('q'),
                'show_filter_type_select': self.filter_type_select_enabled and filters,
                'current_type': self.get_filter_type(),
            }
        )
        return context
