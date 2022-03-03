# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re


from cosinnus.core.registries.group_models import group_model_registry
from django.core.exceptions import ImproperlyConfigured
from django.conf.urls import url


class APIRegexURLResolver(object):
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

    
def simple_api_pattern_generator(version, pattern_list, app=None, add_groups=False,
                 default_kwargs=None, app_name=None, url_group_key=None, namespace=None):
    
    api_regex = '^api/v%d/' % version
    if add_groups:
        if not url_group_key:
            raise ImproperlyConfigured('Add groups was set to True for API URL matcher, but no group url key was specified!')
        api_regex += '%s/(?P<group>[^/]+)/' % url_group_key
    if app is not None:
        api_regex += '%s/' % app
    api_regex += '%s$'
    
    generated_api_patterns = []
    for url_pattern in pattern_list:
        path = url_pattern.pattern._regex[1:] # take the url regex pattern without the leading '^'
        generated_api_patterns.append(url(api_regex % path, url_pattern.callback, name=url_pattern.name))
    return generated_api_patterns


def api_patterns(version, app=None, add_groups=False, *args):
    assert isinstance(version, int)
    pattern_list = [*args]
    if add_groups:
        patterns = []
        for url_key in group_model_registry:
            patterns.extend(simple_api_pattern_generator(version, pattern_list, app=app, url_group_key=url_key,
                                add_groups=add_groups))
        return patterns
    else:
        return simple_api_pattern_generator(version, pattern_list, app=app, url_group_key=None,
                                add_groups=add_groups)
        
