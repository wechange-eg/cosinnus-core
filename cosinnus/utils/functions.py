# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.importlib import import_module
from uuid import uuid1
from django.core.exceptions import ImproperlyConfigured
from django.utils.text import normalize_newlines, unescape_entities
from django.utils.html import strip_tags
from django.utils.encoding import force_text
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import six


def unique_aware_slugify(item, slug_source, slug_field, 
        extra_conflict_check=lambda slug: False, force_redo=False, **kwargs):
    """Ensures a unique slug field by appending an integer counter to duplicate
    slugs.

    The item's slug field is first prepopulated by slugify-ing the source
    field up to the maximum length of the slug field - 5. If that value already
    exists, a counter is appended to the slug, and the counter incremented
    upward until the value is unique. The maximum counter is therefor 9999.

    For instance, if you save an object titled "Daily Roundup", and the slug
    "daily-roundup" is already taken, this function will try "daily-roundup-2",
    "daily-roundup-3", "daily-roundup-4", etc, until a unique value is found.

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
    :param lambda/func extra_conflict_check: A function that takes
        a candidate slug as argument, and returns True if a clash exists
        for that slug. Used as an additional constraining check on whether a 
        slug should not be used.
        Default: lambda slug: False
    :param bool force_redo: If False, will do nothing if a slug is already set
        on the item. If True, will redo the slugification, but exclude the 
        currently set slug from the list, meaning that if all other constraints
        are clean, an item will keep its slug, but if the current slug clashes,
        it will be redone.
    :param kwargs: Additional filter attributes on applied to the model
    """
    import re
    from django.template.defaultfilters import slugify
    
    # We always re-do slugific if the force_switch is on, but then exclude the current slug
    # from the clash list
    own_slug = getattr(item, slug_field)
    if own_slug and not force_redo:
        # if a slug is already set, do nothing but return
        return
    
    max_length = item._meta.get_field_by_name(slug_field)[0].max_length
    slug_len = max_length - 10  # 1 for '-'and 4 (+5 for etherpad-id compatibility) for the counter
    slug = slugify(getattr(item, slug_source)[:slug_len])
    
    # sanity check, we can never ever have an empty slug!
    # note: cyrillic-only names will slugify to empty, so generate a uuid
    # (unless the slug field has already been filled before)
    if not slug:
        if getattr(item, slug_field, None):
            slug = getattr(item, slug_field)
        else:
            slug = str(uuid1().int)[:10]
    
    # resolve proxy classes to their lowest common database model
    model = item.__class__
    while model._meta.proxy:
        model =  model.__bases__[0]
        
    # the following gets all existing slug values
    if slug_field not in kwargs:
        kwargs['%s__startswith' % slug_field] = slug
    # be unique_together aware:
    for unique_list in model._meta.unique_together:
        if slug_field in unique_list:
            for unique_field in unique_list:
                if not unique_field == slug_field:
                    kwargs[unique_field] = getattr(item, unique_field, None)
    
    all_slugs = list(model.objects.filter(**kwargs).values_list(slug_field, flat=True))
    if force_redo:
        # remove own slug from clash list
        all_slugs = [clash_slug for clash_slug in all_slugs if clash_slug != own_slug]
    
    if slug in all_slugs or extra_conflict_check(slug):
        finder = re.compile(r'-\d+$')
        counter = 2
        slug = '%s-%d' % (slug, counter)
        while slug in all_slugs or extra_conflict_check(slug):
            slug = re.sub(finder, '-%d' % counter, slug)
            counter += 1
    # set the slug
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
    
    
def resolve_class(path_to_class):
    modulename, _, klass = path_to_class.rpartition('.')
    module = import_module(modulename)
    cls = getattr(module, klass, None)
    if cls is None:
        raise ImportError("Cannot import class %s from %s" % (
            klass, path_to_class))
    return cls


def ensure_dict_keys(mydict, keys=[], message=""):
    """ Raises an ImproperlyConfigured if not all supplied key strings
        are contained in the given dictionary. """
    missing_keys = []
    for key in keys:
        if not key in mydict:
            missing_keys.append(key)
    if missing_keys:
        if not message:
            message = "The given dictionary is missing the following keys: '%s'"
        if not "%s" in message:
            message += ': %s'
        raise ImproperlyConfigured(message % ", ".join(missing_keys))


def clean_single_line_text(text):
    """ Removes linebreaks, tabs and leading/traling spaces.
        Used for all object titles and group names. """
    text = normalize_newlines(text).replace('\n', '').replace('\t', '').strip()
    return text


def convert_html_to_string(text):
    """ Returns text containing html tags as text without its tags """
    return unescape_entities(strip_tags(force_text(text)))


def is_number(s):
    """ Check if value is a number """
    try:
        float(s)
        return True
    except ValueError:
        return False


def resolve_attributes(obj, attr_or_function, default=None):    
    """ Returns the given string attribute of an object, or its return value if it's a function.
        If None given, or the object had no such attribute or function, try to find
        the given default attribute. If no default given, return None. 
        This function takes stacked attributes, much like a django template would.
        
        ``resolve_attributes(user, 'cosinnus_profile.language.get_absolute_url')``
             would return the value of ``user.cosinnus_profile.get_absolute_url()`` """
        
    attribute = None
    if attr_or_function:
        # pick and resolve first attribute in string
        attributes = attr_or_function.split('.', 1)
        attribute = attributes[0]
        rest_attributes = attributes[1] if len(attributes) > 1 else None
    
    # if no attribute was given or the given object does not contain that attribute, try to resolve
    # the default attribute on the object, or return the default
    if not attribute or not getattr(obj, attribute, None):
        return resolve_attributes(obj, default) if (default and default != attr_or_function) else None
    
    resolved_attr = getattr(obj, attribute, None)
    value = resolved_attr() if hasattr(resolved_attr, '__call__') else resolved_attr
    
    # recurse as long as there are stacked attributed in the string
    if rest_attributes:
        return resolve_attributes(value, rest_attributes, default)
    else:
        return value


def is_email_valid(email):
    """ Returns True if the given email is a valid email address, False else """
    try:
        validate_email( email )
        return True
    except ValidationError:
        return False
    
def ensure_list_of_ints(value):
    """ Will accept a single int/str number or list or comma-seperated list of int/str numbers
        and always return a list of integers, or an empty list """
    # guarantee list of ints
    if value is None or value == '' or value == []:
        return []
    if isinstance(value, six.string_types):
        if ',' in value:
            value = [int(val) for val in value.split(',')]
        else:
            value = [int(value)]
    elif isinstance(value, int):
        value = [value]
    elif isinstance(value, list):
        value = [int(val) for val in value]
    return value
    