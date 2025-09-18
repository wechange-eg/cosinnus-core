# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Type, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, QuerySet
from django.db.models.fields import DateField
from django.db.models.functions.datetime import TruncBase, TruncDay, TruncMonth, TruncWeek, TruncYear
from django.http import HttpResponseRedirect
from django.utils.formats import localize
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView

from cosinnus.forms.statistics import SimpleStatisticsForm
from cosinnus.models import UserOnlineOnDay
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.utils.user import filter_active_users
from cosinnus.views.mixins.group import RequirePortalManagerMixin

# how many past days to show by default
DATE_RANGE_DEFAULT_PAST_DAYS = 30


class _BaseInterval(ABC):
    """encapsulates interval_type specific logic"""

    trunc_function: Type[TruncBase]

    @classmethod
    @abstractmethod
    def format_label(cls, reference_date: date) -> str:
        """format the date as string according to interval_type"""
        pass

    @classmethod
    @abstractmethod
    def get_current_start(cls, reference_date: date) -> date:
        """return start date of current interval possibly in the past"""
        pass

    @classmethod
    @abstractmethod
    def get_next_start(cls, aligned_date: date) -> date:
        """
        return the start date of the next interval

        Note: argument must be aligned to interval start
        """
        pass

    @classmethod
    def get_trunc_function(cls) -> Type[TruncBase]:
        """return trunc function-class to filter a django queryset"""
        return cls.trunc_function

    @classmethod
    def get_interval_type_from_date_range(cls, date_from: date, date_to: date) -> Type['_BaseInterval']:
        """
        returns an interval-type class depending on the timedelta between date_from and date_to
        """
        timedelta_days = (date_to - date_from).days
        if timedelta_days < 30:
            return _DayInterval
        elif timedelta_days < 90:
            return _WeekInterval
        elif timedelta_days < 1080:
            return _MonthInterval
        else:
            return _YearInterval


class _DayInterval(_BaseInterval):
    trunc_function = TruncDay

    @classmethod
    def format_label(cls, reference_date: date) -> str:
        return reference_date.strftime('%Y-%m-%d')

    @classmethod
    def get_current_start(cls, reference_date: date) -> date:
        return reference_date

    @classmethod
    def get_next_start(cls, aligned_date: date) -> date:
        return aligned_date + timedelta(days=1)


class _WeekInterval(_BaseInterval):
    trunc_function = TruncWeek

    @classmethod
    def format_label(cls, reference_date: date) -> str:
        return _('Week {week_number}: {week_start_date}').format(
            week_number=reference_date.isocalendar()[1], week_start_date=reference_date.strftime('%Y-%m-%d')
        )

    @classmethod
    def get_current_start(cls, unaligned_date: date) -> date:
        return unaligned_date - timedelta(days=unaligned_date.weekday())

    @classmethod
    def get_next_start(cls, aligned_date: date) -> date:
        return aligned_date + timedelta(weeks=1)


class _MonthInterval(_BaseInterval):
    trunc_function = TruncMonth

    @classmethod
    def format_label(cls, reference_date: date) -> str:
        return reference_date.strftime('%Y-%m')

    @classmethod
    def get_current_start(cls, unaligned_date: date) -> date:
        return unaligned_date.replace(day=1)

    @classmethod
    def get_next_start(cls, aligned_date: date) -> date:
        year = aligned_date.year + (aligned_date.month // 12)
        month = (aligned_date.month % 12) + 1
        return aligned_date.replace(year=year, month=month, day=1)


class _YearInterval(_BaseInterval):
    trunc_function = TruncYear

    @classmethod
    def format_label(cls, reference_date: date) -> str:
        return reference_date.strftime('%Y')

    @classmethod
    def get_current_start(cls, unaligned_date: date) -> date:
        return unaligned_date.replace(month=1, day=1)

    @classmethod
    def get_next_start(cls, aligned_date: date) -> date:
        return date(aligned_date.year + 1, 1, 1)


def _get_formatted_interval_data(
    data: QuerySet, unique_field: str, date_field: str, date_from: date, date_to: date
) -> List[Tuple[str, int]]:
    """
    queries interval-data aggregated in buckets, formats to be displayed as chart

    - formats date value as string depending on the interval_type
    - handles incomplete intervals at the edges (labels them appropriately)
    - fills gaps in bucket_range with 0 value-intervals
    :return: continuous range of aligned interval data as '(date,value)'
    """
    # get interval class for date range to lookup interval-specific functions
    interval_type = _BaseInterval.get_interval_type_from_date_range(date_from, date_to)

    # query database aggregating to buckets, ensure date is type datime.date, returning as list of tuples
    #   the first .values() annotates with _temp_bucket_date and specifies its fields as group_by-fields
    #   the .annotate() adds the counts
    #   the .values_list() makes the result format explicit
    trunc_function = interval_type.get_trunc_function()
    data_buckets_list = (
        data.values(_temp_bucket_date=trunc_function(date_field, output_field=DateField()))
        .annotate(_temp_bucket_count=Count(unique_field, distinct=True))
        .values_list('_temp_bucket_date', '_temp_bucket_count')
    )

    # walk the date range by interval, insert bucket values or 0 if missing
    data_buckets_lookup: Dict[date, int] = dict(data_buckets_list)
    result = []
    # begin at start of first interval
    interval_current: date = interval_type.get_current_start(date_from)
    while interval_current <= date_to:
        # not using localize(), we format as iso-dates according to interval_type for better chart-layout
        bucket_label = interval_type.format_label(interval_current)

        # amend interval label on first/last interval if it is incomplete
        #   put actual limit dates on new line in parentheses
        if date_from > interval_current:
            bucket_label = bucket_label + '\n(' + _('since %(date_from)s') % {'date_from': date_from.isoformat()} + ')'
        elif date_to < interval_type.get_next_start(interval_current) - timedelta(days=1):
            bucket_label = bucket_label + '\n(' + _('until %(date_to)s') % {'date_to': date_to.isoformat()} + ')'

        result.append((bucket_label, data_buckets_lookup.get(interval_current, 0)))
        interval_current = interval_type.get_next_start(interval_current)
    return result


def _get_statistics_for_metric(
    title: str,
    data: QuerySet,
    unique_field: str,
    date_field: str,
    datetime_from: Optional[datetime],
    datetime_to: Optional[datetime],
    get_buckets: bool = True,
) -> Dict[str, Union[str, int, Dict[Optional[List[str]], Optional[List[int]]]]]:
    """
    Computes metrics for the given model and `unique_field`
    - distinct total count
    - (optional) series with bucket counts aggregated on given
      `date_field` by day/week/month/year depending on the range of the date-slice

    notes:
    - counts distinct entries, filtered according to `unique_field`
    - filters results to the given date-slice (limit can be set on one or both sides, none to disable)
    - bucket generation
        - is disabled unless both date-limits are set
        - can be disabled via `get_buckets=False`
    - date conversion does not consider time-zones!

    :param title: title of the metric
    :param data: data to be aggregated, series of entries with a date/datetime field
    :param unique_field: field name in the `data` queryset, used to customize counting distinct items
                        (can be set to `pk` to count all items)
    :param date_field: field name in the `data` queryset, used to filter the data and to create date-intervals
    :param datetime_from: disregard all entries before (set time to 00:00)
    :param datetime_to: disregard all entries after (set time to 23:59)
    :param get_buckets: whether to compute buckets per interval for drawing a chart
    :returns: a dict with title, labels and values for display via `chart.js`.
    """
    # filter the source data by date, if from and/or to is provided
    #   this uses datetime parameters to ensure, we get all objects
    filter_kwargs = {}
    if datetime_from:
        filter_kwargs.update({f'{date_field}__gte': datetime_from})
    if datetime_to:
        filter_kwargs.update({f'{date_field}__lte': datetime_to})
    data_filtered = data.filter(**filter_kwargs)

    # compute total unique count
    total: int = data_filtered.values(unique_field).distinct().count()

    # compute buckets
    bucket_labels = None
    bucket_values = None
    if get_buckets:
        if not datetime_from and not datetime_to:
            raise ValueError('bucket generation needs date_from and date_to to be set')

        # from here on we only use dates
        date_from = datetime_from.date()
        date_to = datetime_to.date()

        # get formatted bucket data
        buckets_formatted: List[Tuple[str, int]] = _get_formatted_interval_data(
            data_filtered, unique_field, date_field, date_from, date_to
        )

        # format buckets for chart.js if present
        bucket_labels = [entry[0].splitlines() for entry in buckets_formatted]
        bucket_values = [entry[1] for entry in buckets_formatted]

    # return statistics as one dict
    return {'title': title, 'total': total, 'buckets': {'labels': bucket_labels, 'values': bucket_values}}


def _get_statistics(from_date: datetime, to_date: datetime) -> list:
    """
    define metrics to be gathered as list items using helper functions
    - params from_date and to_date are datetime objects to make filtering querysets easier
    :return: list of metric-data as dicts
    """

    statistics: list = []

    # active users
    # the first recorded user online date (when the feature went live)
    first_online_date: date = UserOnlineOnDay.objects.all().order_by('date').first().date
    # only show the info, if this affects the current request

    first_online_str = (
        # Translators: keep formatting verbatim (space, parenthesis)
        _(' (recorded only from {first_online_date} onwards)').format(
            first_online_date=f'<span style="white-space: nowrap;">{localize(first_online_date)}</span>'
        )
        if first_online_date > from_date.date()
        else ''
    )
    statistics.append(
        _get_statistics_for_metric(
            # Translators: no punctuation at the end
            title=_('Unique, registered users that were active in this period') + first_online_str,
            data=UserOnlineOnDay.objects.filter(user_id__in=CosinnusPortal.get_current().members),
            unique_field='user__id',
            date_field='date',
            datetime_from=from_date,
            datetime_to=to_date,
        )
    )

    # registered users
    # not using cosinnus.utils.user.filter_active_users because we want to deactivated accounts
    used_user_accounts = (
        get_user_model()
        .objects.filter(id__in=CosinnusPortal.get_current().members)
        .exclude(last_login__exact=None)
        .exclude(email__icontains='__unverified__')
        .filter(cosinnus_profile__tos_accepted=True)
        .exclude(cosinnus_profile___is_guest=True)
    )
    statistics.append(
        _get_statistics_for_metric(
            title=_('New Registered User Accounts in this period'),
            data=used_user_accounts,
            unique_field='pk',
            date_field='date_joined',
            datetime_from=from_date,
            datetime_to=to_date,
        )
    )

    # total enabled user-accounts (excluding deactivated accounts)
    statistics.append(
        _get_statistics_for_metric(
            title=_('Total Enabled User Accounts (at least 1x logged in)'),
            data=filter_active_users(get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members)),
            unique_field='pk',
            date_field='date_joined',
            datetime_from=None,
            datetime_to=to_date,
            get_buckets=False,
        )
    )

    # created projects
    statistics.append(
        _get_statistics_for_metric(
            title=_('Newly Created Projects in this period'),
            data=CosinnusProject.objects.filter(portal=CosinnusPortal.get_current()),
            unique_field='pk',
            date_field='created',
            datetime_from=from_date,
            datetime_to=to_date,
        )
    )

    # enabled projects
    statistics.append(
        _get_statistics_for_metric(
            title=_('Total Enabled Projects'),
            data=CosinnusProject.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            datetime_from=None,
            datetime_to=to_date,
            get_buckets=False,
        )
    )

    # created groups
    statistics.append(
        _get_statistics_for_metric(
            title=_('Newly Created Groups in this period'),
            data=CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current()),
            unique_field='pk',
            date_field='created',
            datetime_from=from_date,
            datetime_to=to_date,
        )
    )

    # enabled groups
    statistics.append(
        _get_statistics_for_metric(
            title=_('Total Enabled Groups'),
            data=CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            datetime_from=None,
            datetime_to=to_date,
            get_buckets=False,
        )
    )

    if settings.COSINNUS_CONFERENCES_ENABLED:
        # created conferences
        statistics.append(
            _get_statistics_for_metric(
                title=_('Newly Created Conferences in this period'),
                data=CosinnusConference.objects.filter(portal=CosinnusPortal.get_current()),
                unique_field='pk',
                date_field='created',
                datetime_from=from_date,
                datetime_to=to_date,
            )
        )

        # enabled conferences
        statistics.append(
            _get_statistics_for_metric(
                title=_('Total Enabled Conferences'),
                data=CosinnusConference.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
                unique_field='pk',
                date_field='created',
                datetime_from=None,
                datetime_to=to_date,
                get_buckets=False,
            )
        )

        # scheduled conferences
        # TODO implement bucket calculation for date ranges manually
        running_conferences_filtered = CosinnusConference.objects.filter(
            portal=CosinnusPortal.get_current(), is_active=True
        ).filter(
            (Q(from_date__gte=from_date) & Q(to_date__lte=to_date))
            | (Q(to_date__gte=from_date) & Q(to_date__lte=to_date))
            | (Q(from_date__lte=from_date) & Q(to_date__gte=to_date))
        )
        statistics.append(
            _get_statistics_for_metric(
                title=_('Running (scheduled) Conferences in this period'),
                data=running_conferences_filtered,
                unique_field='pk',
                date_field='created',
                datetime_from=from_date,
                datetime_to=to_date,
                get_buckets=False,
            )
        )

    # optional: 11. Newly Created Events in this period
    try:
        from cosinnus_event.models import Event

        statistics.append(
            _get_statistics_for_metric(
                title=_('Newly Created Events in this period'),
                data=Event.objects.filter(group__portal=CosinnusPortal.get_current()),
                unique_field='pk',
                date_field='created',
                datetime_from=from_date,
                datetime_to=to_date,
            )
        )
        return statistics
    except Exception:
        pass

    # optional: 12. Newly Created News in this period
    try:
        from cosinnus_note.models import Note

        statistics.append(
            _get_statistics_for_metric(
                title=_('Newly Created News in this period'),
                data=Note.objects.filter(group__portal=CosinnusPortal.get_current()),
                unique_field='pk',
                date_field='created',
                date_from=from_date,
                date_to=to_date,
            )
        )
    except Exception:
        pass

    return statistics


class SimpleStatisticsView(RequirePortalManagerMixin, FormView):
    DATE_FORMAT = '%Y-%m-%d-%H:%M'

    form_class = SimpleStatisticsForm
    template_name = 'cosinnus/statistics/simple.html'

    def dispatch(self, request, *args, **kwargs):
        # add default date range if none is given
        if request.method == 'GET' and ('from' not in request.GET or 'to' not in request.GET):
            date_to = datetime.now().replace(hour=23, minute=59)
            date_from = (datetime.now() - timedelta(days=DATE_RANGE_DEFAULT_PAST_DAYS)).replace(hour=0, minute=0)

            parameters = request.GET.copy()
            parameters['to'] = date_to.strftime(self.DATE_FORMAT)
            parameters['from'] = date_from.strftime(self.DATE_FORMAT)
            redirect_url = f'{request.path}?{parameters.urlencode()}'

            return HttpResponseRedirect(redirect_url)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self, *args, **kwargs):
        initial = super(SimpleStatisticsView, self).get_initial(*args, **kwargs)
        if self.request.method == 'GET' and 'from' in self.request.GET and 'to' in self.request.GET:
            initial.update(
                {
                    'from_date': datetime.strptime(self.request.GET.get('from'), SimpleStatisticsView.DATE_FORMAT),
                    'to_date': datetime.strptime(self.request.GET.get('to'), SimpleStatisticsView.DATE_FORMAT),
                }
            )
        return initial

    def get_context_data(self, *args, **kwargs):
        context = super(SimpleStatisticsView, self).get_context_data(*args, **kwargs)
        if self.request.method == 'GET' and 'from' in self.request.GET and 'to' in self.request.GET:
            # this is datetime with time set from 00:00 to 23:59 to
            # include all objects in filter queries with datetime-fields
            from_date: datetime = context['form'].initial['from_date']
            to_date: datetime = context['form'].initial['to_date']
            context.update({'statistics': _get_statistics(from_date, to_date)})
        return context

    def form_valid(self, form):
        self.form = form
        return super(SimpleStatisticsView, self).form_valid(form)

    def get_success_url(self):
        params = {
            'from': self.form.cleaned_data['from_date'].strftime(SimpleStatisticsView.DATE_FORMAT),
            'to': self.form.cleaned_data['to_date'].strftime(SimpleStatisticsView.DATE_FORMAT),
        }
        return '.?from=%(from)s&to=%(to)s' % params


simple_statistics = SimpleStatisticsView.as_view()
