# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
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


class QuerysetLazyCombiner:
    """ Iterator that lazyily combines items from multiple sorted querysets by picking
        the one highest sorted item from all of the querysets at each step.
        Will laziliy fetch only `peek_amount` items from each queryset until more are 
        needed.
        Note: It is required that all querysets are already `.order_by()`ed by the 
        given`order_key`!
    """
    
    querysets = None # list
    queryset_map = None # dict
    queryset_offset_map = None # dict
    buffer_map = None # dict
    
    peek_amount = 10 # how many instances are fetched from each queryset at once
    order_key = None # the model attribute 
    reverse = False # sort the order_key reversed
    
    def __init__(self, querysets, order_key, peek_amount=10, reverse=False):
        """ 
            @param querysets: a list of ordered querysets. each model instance must have
                the field specified in `order_key`
            @param order_key: the model field by which queryset instances are sorted
            @param peek_amount: the number of items fetched from each queryset at a time
            @param reverse: if True, sort order using `order_key` is reversed
        """
        self.querysets = querysets
        self.order_key = order_key
        self.peek_amount = peek_amount
        self.reverse = reverse

    def __iter__(self):
        self.queryset_map = {}
        self.buffer_map = {}
        self.queryset_offset_map = {}
        for i in range(len(self.querysets)):
            self.queryset_map[i] = self.querysets[i].all()
            self.queryset_offset_map[i] = 0
            self.buffer_map[i] = None
        return self
        
    def __next__(self):
        # check if buffers need to be refilled
        keys = list(self.buffer_map.keys())
        for i in keys:
            buffer = self.buffer_map[i]
            if not buffer:
                # refill buffer from queryset
                new_offset = self.queryset_offset_map[i]+self.peek_amount
                qs = self.queryset_map[i]
                buffer = list(qs[self.queryset_offset_map[i]:new_offset])
                
                if not buffer:
                    # if queryset was exhausted, remove it and the buffer from the maps
                    del self.queryset_map[i]
                    del self.queryset_offset_map[i]
                    del self.buffer_map[i]
                else:
                    # otherwise, set new offset and buffer map
                    self.queryset_offset_map[i] = new_offset
                    self.buffer_map[i] = buffer
                    
        # buffers are now refilled, or removed if their queryset was exhausted
        # if no buffers remain, the iterator is exhausted
        if len(self.buffer_map) == 0:
            raise StopIteration
        
        # make a set of candidates and sort it by the sort_key, select from all buffers' first elements
        # the highest sorted one (buffers are sorted), and remove it from the buffer
        candidates = ((buffer[0], i) for i, buffer in self.buffer_map.items())
        candidates = sorted(candidates, key=lambda tup: getattr(tup[0], self.order_key), reverse=self.reverse)
        winning_item, winning_buffer = candidates[0]
        
        del self.buffer_map[winning_buffer][0]
        return winning_item
        
