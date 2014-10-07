# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.conf.urls import patterns
from django.core.urlresolvers import RegexURLResolver

from cosinnus.core.registries.group_models import group_model_registry
from django.core.exceptions import ImproperlyConfigured


class APIRegexURLResolver(RegexURLResolver):
    """
    A URL resolver that always matches the active language code as URL prefix.

    Rather than taking a regex argument, we just override the ``regex``
    function to always return the active language-code as regex.
    """
    def __init__(self, version, urlconf_name, app=None, add_groups=False,
                 default_kwargs=None, app_name=None, url_group_key=None, namespace=None):
        super(APIRegexURLResolver, self).__init__(
            None, urlconf_name, default_kwargs, app_name, namespace)
        self.version = version
        self.app = app
        self.add_groups = add_groups
        self.url_group_key = url_group_key

    @property
    def regex(self):
        lookup = (self.version, self.app, self.add_groups)
        if lookup not in self._regex_dict:
            pattern = '^api/v%d/' % self.version
            if self.add_groups:
                if not self.url_group_key:
                    raise ImproperlyConfigured('Add groups was set to True for API URL matcher, but no group url key was specified!')
                pattern += '%s/(?P<group>[^/]+)/' % self.url_group_key
            if self.app is not None:
                pattern += '%s/' % self.app
            regex_compiled = re.compile(pattern, re.UNICODE)
            self._regex_dict[lookup] = regex_compiled
        return self._regex_dict[lookup]


def api_patterns(version, app=None, add_groups=False, prefix='', *args):
    assert isinstance(version, int)
    pattern_list = patterns(prefix, *args)
    if add_groups:
        return [APIRegexURLResolver(version, pattern_list, app=app, url_group_key=url_key,
                                add_groups=add_groups) for url_key in group_model_registry]
    else:
        return [APIRegexURLResolver(version, pattern_list, app=app, url_group_key=None,
                                add_groups=add_groups) ]
        
