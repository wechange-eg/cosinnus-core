# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def unique_aware_slugify(item, slug_source, slug_field, **fkwargs):
    """Ensures a unique slug field by appending an integer counter to duplicate
    slugs.

    The item's slug field is first prepopulated by slugify-ing the source
    field. If that value already exists, a counter is appended to the slug, and
    the counter incremented upward until the value is unique.

    For instance, if you save an object titled “Daily Roundup”, and the slug
    “daily-roundup” is already taken, this function will try “daily-roundup-2”,
    “daily-roundup-3”, “daily-roundup-4”, etc, until a unique value is found.

    Call from within a model's custom save() method like::

        unique_aware_slugify(self, slug_source='title', slug_field='slug')

    where the value of field slug_source will be used to prepopulate the value
    of slug_field.

    The any additional arguments passed to this function are used during lookup
    existing slugs and can be used to filter them.
    """
    import re
    from django.template.defaultfilters import slugify
    s = getattr(item, slug_field)
    if s:
        # if a slug is already set, do nothing but return
        return

    slug = slugify(getattr(item, slug_source))
    model = item.__class__
    # the following gets all existing slug values
    if not slug_field in fkwargs:
        fkwargs['%s__startswith' % slug_field] = slug
    all_slugs = list(model.objects.filter(**fkwargs).values_list(slug_field, flat=True))
    if slug in all_slugs:
        finder = re.compile(r'-\d+$')
        counter = 2
        slug = '%s-%d' % (slug, counter)
        while slug in all_slugs:
            slug = re.sub(finder, '-%d' % counter, slug)
            counter += 1
    setattr(item, slug_field, slug)
