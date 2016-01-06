# -*- coding: utf-8 -*-

from django.utils.html import format_html

from wagtail.wagtailcore import hooks, fields
from wagtail.wagtailcore.whitelist import attribute_rule
from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
fields

@hooks.register('insert_editor_js')
def enable_source():
    return format_html(
        """
        <script>
          registerHalloPlugin('hallojustify');
          registerHalloPlugin('hallohtml');
          // replaces non-existant HTML button icon
          $('body').on('halloactivated', function(){{ 
              $('.icon-list-alt').addClass('icon-code').removeClass('icon-list-alt'); 
          }});
        </script>
        """
    )

@hooks.register('insert_editor_css')
def editor_css():
    css_string = '<link rel="stylesheet" href="%s">' % static('css/vendor/font-awesome.min.css')
    if settings.DEBUG:
        css_string += '<link rel="stylesheet/less" href="%s">' % static('less/cosinnus.less')
        css_string += '<script src="%s"></script>' % static('js/vendor/less.min.js')
    else:
        css_string += '<link rel="stylesheet" href="%s">' % static('css/cosinnus.css')
    return format_html(css_string)

def allow_all_attributes(attribute_value):
    class Fn_get_true(object):
        def get(self, *args, **kwargs):
            return True
    return attribute_rule(Fn_get_true())

@hooks.register('construct_whitelister_element_rules')
def whitelister_element_rules():
    return {
        'iframe': allow_all_attributes,
        'small': allow_all_attributes,
        
        '[document]': allow_all_attributes,
        'a': allow_all_attributes,
        'b': allow_all_attributes,
        'br': allow_all_attributes,
        'div': allow_all_attributes,
        'em': allow_all_attributes,
        'h1': allow_all_attributes,
        'h2': allow_all_attributes,
        'h3': allow_all_attributes,
        'h4': allow_all_attributes,
        'h5': allow_all_attributes,
        'h6': allow_all_attributes,
        'hr': allow_all_attributes,
        'i': allow_all_attributes,
        'img': allow_all_attributes,
        'li': allow_all_attributes,
        'ol': allow_all_attributes,
        'p': allow_all_attributes,
        'strong': allow_all_attributes,
        'sub': allow_all_attributes,
        'sup': allow_all_attributes,
        'ul': allow_all_attributes,
    }
    