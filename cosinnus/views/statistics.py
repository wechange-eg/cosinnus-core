# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import calendar
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek, TruncYear
from django.utils.formats import localize
from django.views.generic.edit import FormView

from cosinnus.forms.statistics import SimpleStatisticsForm
from cosinnus.models import UserOnlineOnDay
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.utils.user import filter_active_users
from cosinnus.views.mixins.group import RequirePortalManagerMixin


def _filter_by_date_maybe(
    data: QuerySet, date_field: str, date_from: Optional[datetime], date_to: Optional[datetime]
) -> QuerySet:
    """
    returns a queryset, filtered according to date_from and date_to, maybe one-sided

    - does return the source queryset unchanged, if both date_from and date_to are None
    """
    # dont filter, if no limits are provided
    if not date_from and not date_to:
        return data

    # construct filter arguments
    filter_kwargs = {}
    if date_from:
        filter_kwargs.update({f'{date_field}__gte': date_from})
    if date_to:
        filter_kwargs.update({f'{date_field}__lte': date_to})

    return data.filter(**filter_kwargs)


def _get_interval_type(date_from: datetime, date_to: datetime) -> str:
    """
    determines the interval type depending on the timedelta between date_from and date_to
    :returns: one of 'day', 'week', 'month', 'year'
    """
    timedelta_days = (date_to - date_from).days
    if timedelta_days < 30:
        return 'day'
    elif timedelta_days < 90:
        return 'week'
    elif timedelta_days < 1080:
        return 'month'
    else:
        return 'year'


def _get_interval_aligned_from_to_timestamps(
    date_from: datetime, date_to: datetime, interval_type: str
) -> Tuple[datetime, datetime]:
    """
    align date_from and date_to to interval length

    - the time range is expanded to include whole intervals
    :return: (date_from, date_to)
    """
    if interval_type == 'day':
        return date_from, date_to
    elif interval_type == 'week':
        # week starts on monday
        # TODO make this configurable?
        date_from -= timedelta(days=date_from.weekday())
        date_to += timedelta(days=(6 - date_to.weekday()))
    elif interval_type == 'month':
        date_from = date_from.replace(day=1)
        last_day = calendar.monthrange(date_to.year, date_to.month)[1]
        date_to = date_to.replace(day=last_day)
    elif interval_type == 'year':
        date_from = date(date_from.year, 1, 1)
        date_to = date(date_to.year, 12, 31)
    else:
        raise ValueError(f'interval type {interval_type} is not supported')

    return date_from, date_to


def _increment_interval(date_current: datetime, interval_type: str) -> datetime:
    """
    increments the interval by one step depending on the interval_type

    :return: start of the next interval
    """

    if interval_type == 'day':
        return date_current + timedelta(days=1)
    elif interval_type == 'week':
        return date_current + timedelta(weeks=1)
    elif interval_type == 'month':
        year = date_current.year + (date_current.month // 12)
        month = (date_current.month % 12) + 1
        return date_current.replace(year=year, month=month, day=1)
    elif interval_type == 'year':
        return date(date_current.year + 1, 1, 1)
    else:
        raise ValueError('Invalid interval type')


def _get_continuos_aligned_interval_data(
    data_buckets: List[Tuple[date, int]], date_from: datetime, date_to: datetime, interval_type: str
) -> List[Tuple[date, int]]:
    """
    ensures that bucket range is ready to be displayed as chart

    - aligns start/end points to be at the beginning or end of an interval
    - fills gaps in bucket_range with 0 values
    :return: continuos range of aligned interval data as 'date:value'
    """

    # FIXME use alignment only for inner buckets and use incomplete buckets at the ends
    # build lookup dict
    lookup_table = {entry[0]: entry[1] for entry in data_buckets}

    date_from_aligned, date_to_aligned = _get_interval_aligned_from_to_timestamps(date_from, date_to, interval_type)

    # walk the date range by interval, insert bucket values or 0 if missing
    result = []
    date_current = date_from_aligned.date()
    while date_current <= date_to_aligned.date():
        result.append((date_current, lookup_table.get(date_current, 0)))
        date_current = _increment_interval(date_current, interval_type)
    return result


def _to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    elif isinstance(value, date):
        return value
    else:
        raise TypeError(f'expected datetime.date or datetime.datetime,got {type(value)}')


def _get_statistics_for_model(
    title: str,
    data: QuerySet,
    unique_field: str,
    date_field: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    get_buckets: bool = True,
):
    """
    Computes metrics for the given model and `unique_field`

    metrics:
    - distinct total count
    - series with bucket counts aggregated on given `date_field` by day/week/month/year depending on the date-slice

    notes:
    - filters results to the given date-slice (limit can be set on one or both sides, none to disable)
    - bucket generation
        - is disabled unless both date-limits are set
        - can be disabled via `get_buckets=False`

    returns a dict with labels and values for display via `chart.js`.
    """
    # filter the source data by date, if from and/or to is provided

    data_filtered = _filter_by_date_maybe(data, date_field, date_from, date_to)

    # compute total unique count
    total: int = data_filtered.values(unique_field).distinct().count()

    # compute buckets according to buckets if date_field is provided
    bucket_labels = None
    bucket_values = None
    if get_buckets:
        if not date_from and not date_to:
            raise ValueError('bucket generation needs date_from and date_to to be set')
        interval_type = _get_interval_type(date_from, date_to)

        # compute buckets
        bucket_function = {'day': TruncDate, 'week': TruncWeek, 'month': TruncMonth, 'year': TruncYear}.get(
            interval_type
        )

        # FIXME make sure annotated field names are not conflicting with existing field names
        data_buckets: Optional[QuerySet] = data_filtered.values(__bucket_date=bucket_function(date_field)).annotate(
            __bucket_count=Count(unique_field, distinct=True)
        )
        buckets_gaps: List[Tuple[date, int]] = [
            (_to_date(entry['__bucket_date']), entry['__bucket_count']) for entry in data_buckets
        ]

        # empty buckets are not listed in the queryset, we need to add 0 values manually
        buckets_continuos: List[Tuple[date, int]] = _get_continuos_aligned_interval_data(
            buckets_gaps, date_from, date_to, interval_type
        )
        bucket_label_filter = {
            'day': lambda x: x.strftime('%Y-%m-%d'),
            'week': lambda x: f"week {x.isocalendar()[1]}: {x.strftime('%Y-%m-%d')}",
            'month': lambda x: x.strftime('%Y-%m'),
            'year': lambda x: x.strftime('%Y'),
        }.get(interval_type)

        # format buckets for chart.js if present
        bucket_labels = [bucket_label_filter(entry[0]) for entry in buckets_continuos]
        bucket_values = [entry[1] for entry in buckets_continuos]

    # return statistics as one dict
    return {'title': title, 'total': total, 'buckets': {'labels': bucket_labels, 'values': bucket_values}}


def _get_statistics(from_date: datetime, to_date: datetime) -> list:
    """Actual collection of data"""

    statistics: list = []

    # active users
    # the first recorded user online date (when the feature went live)
    first_online_date: date = UserOnlineOnDay.objects.all().order_by('date').first().date
    # only show the info, if this affects the current request
    first_online_str = (
        f' (recorded only from {localize(first_online_date)} onwards)' if first_online_date > from_date.date() else ''
    )
    statistics.append(
        _get_statistics_for_model(
            title=f'01. Unique, registered users that were active in this period{first_online_str}',
            data=UserOnlineOnDay.objects.filter(user_id__in=CosinnusPortal.get_current().members),
            unique_field='user__id',
            date_field='date',
            date_from=from_date,
            date_to=to_date,
        )
    )

    # registered users
    statistics.append(
        _get_statistics_for_model(
            title='02. New Registered User Accounts in this period',
            data=filter_active_users(get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members)),
            unique_field='pk',
            date_field='date_joined',
            date_from=from_date,
            date_to=to_date,
        )
    )

    # total enabled user-accounts
    statistics.append(
        _get_statistics_for_model(
            title='03. Total Enabled User Accounts (at least 1x logged in)',
            data=filter_active_users(get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members)),
            unique_field='pk',
            date_field='date_joined',
            date_from=None,
            date_to=to_date,
            get_buckets=False,
        )
    )

    # created projects
    statistics.append(
        _get_statistics_for_model(
            title='04. Newly Created Projects in this period',
            data=CosinnusProject.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            date_from=from_date,
            date_to=to_date,
        )
    )

    # enabled projects
    statistics.append(
        _get_statistics_for_model(
            title='05. Total Enabled Projects',
            data=CosinnusProject.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            date_from=None,
            date_to=to_date,
            get_buckets=False,
        )
    )

    # created groups
    statistics.append(
        _get_statistics_for_model(
            title='06. Newly Created Groups in this period',
            data=CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            date_from=from_date,
            date_to=to_date,
        )
    )

    # enabled groups
    statistics.append(
        _get_statistics_for_model(
            title='07. Total Enabled Groups',
            data=CosinnusSociety.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            date_from=None,
            date_to=to_date,
            get_buckets=False,
        )
    )

    # created conferences
    statistics.append(
        _get_statistics_for_model(
            title='08. Newly Created Conferences in this period',
            data=CosinnusConference.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            date_from=from_date,
            date_to=to_date,
        )
    )

    # enabled conferences
    statistics.append(
        _get_statistics_for_model(
            title='09. Total Enabled Conferences',
            data=CosinnusConference.objects.filter(portal=CosinnusPortal.get_current(), is_active=True),
            unique_field='pk',
            date_field='created',
            date_from=None,
            date_to=to_date,
            get_buckets=False,
        )
    )

    # scheduled conferences
    # FIXME buckets need to be calculated differently
    running_conferences_filtered = CosinnusConference.objects.filter(
        portal=CosinnusPortal.get_current(), is_active=True
    ).filter(
        (Q(from_date__gte=from_date) & Q(to_date__lte=to_date))
        | (Q(to_date__gte=from_date) & Q(to_date__lte=to_date))
        | (Q(from_date__lte=from_date) & Q(to_date__gte=to_date))
    )
    statistics.append(
        _get_statistics_for_model(
            title='10. Running (scheduled) Conferences in this period',
            data=running_conferences_filtered,
            unique_field='pk',
            date_field='created',
            date_from=from_date,
            date_to=to_date,
            get_buckets=False,
        )
    )

    # optional: 11. Newly Created Events in this period
    try:
        from cosinnus_event.models import Event

        statistics.append(
            _get_statistics_for_model(
                title='11. Newly Created Events in this period',
                data=Event.objects.filter(group__portal=CosinnusPortal.get_current()),
                unique_field='pk',
                date_field='created',
                date_from=from_date,
                date_to=to_date,
            )
        )
        return statistics
    except Exception:
        pass

    # optional: 12. Newly Created News in this period
    try:
        from cosinnus_note.models import Note

        statistics.append(
            _get_statistics_for_model(
                title='12. Newly Created News in this period',
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
