# -*- coding: utf-8 -*-
"""
The cosinnus app ecosystem allows apps to provide certain functionality that
can be used from cosinnus core as well as other (cosinnus) apps.

The initial implementation adapts the ``ActionRegistry`` or
``DynamicFormFieldRegistry`` from ``django-dynamic-forms``
https://github.com/Markush2010/django-dynamic-forms/tree/f306619e12

"""

from __future__ import unicode_literals

from collections import OrderedDict
import six
import threading


class BaseRegistry(object):
    """
    The :class:`BaseRegistry` provides a basic layout each registry should use.
    The main idea is to provide locking while registering new objects.

    Subclasses **must** implement a :meth:`register` function.
    """

    def __init__(self):
        self.lock = threading.Lock()

    def register(self, *args, **kwargs):
        """
        Registers a new item in the registry.

        Implement something like:

        .. code-block:: python

            def register(self, *args, **kwargs):
                with self.lock:
                    # Here comes my fancy registration logic

        """
        raise NotImplementedError('Subclasses need to implement this method.')


class DictBaseRegistry(BaseRegistry):
    """
    The :class:`DictBaseRegistry` provides an key-value storage for registered
    objects. These objects will be stored in the order they are being
    registered.

    Furthermore an instance of a :class:`DictBaseRegistry` provides container
    features like

    .. code-block:: python

        some_item = my_dict_registry['some-item']

        other_item = my_dict_registry.get('other-item')  # None
        other_item = my_dict_registry.get('other-item', 'default')  # 'default'

        my_dict_registry['some-item'] = 'something else'

        del my_dict_registry['some-item']

    as well as

    .. code-block:: python

        if 'some-item' in my_dict_registry:
            # Do something

        for key in my_dict_registry:
            val = my_dict_registry[k]

    """

    def __init__(self):
        super(DictBaseRegistry, self).__init__()
        with self.lock:
            self._storage = OrderedDict([])

    def __getitem__(self, key):
        return self._storage[key]

    def __setitem__(self, key, value):
        with self.lock:
            self._storage[key] = value

    def __delitem__(self, key):
        del self._storage[key]

    def __iter__(self):
        return six.iterkeys(self._storage)

    def __contains__(self, key):
        return key in self._storage

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def unregister(self, key):
        """
        Locks the internal storage and removes the object described by the
        given key from the storage if it exists.
        """
        if key in self:
            del self[key]
