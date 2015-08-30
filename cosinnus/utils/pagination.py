# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def pagination(objects, per_page, querydict):
    paginator = Paginator(objects, per_page)
    querydict_no_page = querydict.copy()
    try:
        page_num = querydict_no_page.pop('page')[0]  # use first 'page' value
    except KeyError:
        page_num = 1
    try:
        page = paginator.page(page_num)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    has_previous = page.has_previous()
    if has_previous:
        previous_page_number = page.previous_page_number()
    else:
        previous_page_number = None

    has_next = page.has_next()
    if has_next:
        next_page_number = page.next_page_number()
    else:
        next_page_number = None

    pagination = {
        'has_previous': has_previous,
        'has_next': has_next,
        'next_page_number': next_page_number,
        'num_pages': paginator.num_pages,
        'number': page.number,
        'object_list': page.object_list,
        'page_numbers': paginator.page_range,
        'previous_page_number': previous_page_number,
        'query': querydict_no_page.urlencode(),
    }
    return pagination


class PaginationTemplateMixin(object):
    """
    Adds pagination data as 'pagination' to context. Also changes the
    context's 'object_list'!
    Requires the attribute 'per_page' to be set in the mixing class!
    """
    def get_context_data(self, *args, **kwargs):
        context = super(PaginationTemplateMixin, self).get_context_data(
            *args, **kwargs)
        context['pagination'] = pagination(
            context['object_list'], self.per_page, self.request.GET)
        context['object_list'] = context['pagination']['object_list']
        return context
