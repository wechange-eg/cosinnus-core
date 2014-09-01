# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def unique_aware_slugify(item, slug_source, slug_field, **kwargs):
    """Ensures a unique slug field by appending an integer counter to duplicate
    slugs.

    The item's slug field is first prepopulated by slugify-ing the source
    field up to the maximum length of the slug field - 5. If that value already
    exists, a counter is appended to the slug, and the counter incremented
    upward until the value is unique. The maximum counter is therefor 9999.

    For instance, if you save an object titled “Daily Roundup”, and the slug
    “daily-roundup” is already taken, this function will try “daily-roundup-2”,
    “daily-roundup-3”, “daily-roundup-4”, etc, until a unique value is found.

    Call from within a model's custom save() method like::

        unique_aware_slugify(self, slug_source='title', slug_field='slug')

    where the value of field `slug_source` will be used to prepopulate the
    value of `slug_field`.

    Any additional arguments passed to this function are used during lookup
    existing slugs and can be used to filter them.

    .. note::

        If `slug_field` is already set this function won't do anything!

    :param Model item: A Django model instance
    :param str slug_source: The name of the field to construct a slug from
    :param str slug_field: The name of the field to write the slug to
    :param kwargs: Additional filter attributes on applied to the model
    """
    import re
    from django.template.defaultfilters import slugify
    s = getattr(item, slug_field)
    if s:
        # if a slug is already set, do nothing but return
        return

    max_length = item._meta.get_field_by_name(slug_field)[0].max_length
    slug_len = max_length - 5  # 1 for '-'and 4 for the counter
    slug = slugify(getattr(item, slug_source)[:slug_len])
    model = item.__class__
    # the following gets all existing slug values
    if slug_field not in kwargs:
        kwargs['%s__startswith' % slug_field] = slug
    all_slugs = list(model.objects.filter(**kwargs).values_list(slug_field, flat=True))
    if slug in all_slugs:
        finder = re.compile(r'-\d+$')
        counter = 2
        slug = '%s-%d' % (slug, counter)
        while slug in all_slugs:
            slug = re.sub(finder, '-%d' % counter, slug)
            counter += 1
    setattr(item, slug_field, slug)
    


def select_related_chain(qs, *args):
    """ Monkey-patch for django < 1.7  to be able to chain multiple calls
    to qs.select_related() without losing the args of the first calls. """
    def _flatten(dic, strin, chain):
        for key, val in dic.items():
            if not val:
                chain.append(strin and strin + '__' + key or key)
            else:
                return _flatten(val, strin and strin + '__' + key or key, chain)
        return chain
    
    prev_args = _flatten(qs.query.select_related, '', [])
    sels = list(args) + prev_args
    return qs.select_related(*sels)
    
    
def get_cosinnus_app_from_class(cls):
    """ Tries to parse the cosinnus app name from any class in a cosinnus app """
    try:
        return cls.__module__.split('.')[0].replace('cosinnus_', '')
    except:
        return '<not-a-cosinnus-module>'
