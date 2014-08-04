'''
Created on 04.08.2014

@author: Sascha 
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from itertools import chain
from django.template.loader import render_to_string
try:
    from urllib.parse import urlencode
except:
    from urllib import urlencode  # noqa

from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from django.forms.widgets import flatatt
try:
    from django.utils.encoding import force_text
except:  # pragma: nocover
    from django.utils.encoding import force_unicode as force_text  # noqa
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


class LinkWidget(forms.Widget):
    def __init__(self, attrs=None, choices=()):
        super(LinkWidget, self).__init__(attrs)

        self.choices = choices

    def value_from_datadict(self, data, files, name):
        value = super(LinkWidget, self).value_from_datadict(data, files, name)
        self.data = data
        return value

    def render(self, name, value, attrs=None, choices=()):
        if not hasattr(self, 'data'):
            self.data = {}
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs)
        output = ['<ul%s>' % flatatt(final_attrs)]
        options = self.render_options(choices, [value], name)
        if options:
            output.append(options)
        output.append('</ul>')
        return mark_safe('\n'.join(output))

    def render_options(self, choices, selected_choices, name):
        selected_choices = set(force_text(v) for v in selected_choices)
        output = []
        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                for option in option_label:
                    output.append(
                        self.render_option(name, selected_choices, *option))
            else:
                output.append(
                    self.render_option(name, selected_choices,
                                       option_value, option_label))
        return '\n'.join(output)

    def render_option(self, name, selected_choices,
                      option_value, option_label):
        option_value = force_text(option_value)
        if option_label == BLANK_CHOICE_DASH[0][1]:
            option_label = _("All")
        data = self.data.copy()
        data[name] = option_value
        selected = data == self.data or option_value in selected_choices
        try:
            url = data.urlencode()
        except AttributeError:
            url = urlencode(data)
        return self.option_string() % {
             'attrs': selected and ' class="selected"' or '',
             'query_string': url,
             'label': force_text(option_label)
        }

    def option_string(self):
        return '<li><a%(attrs)s href="?%(query_string)s">%(label)s</a></li>'
    


class DropdownChoiceWidget(forms.Widget):
    template_name = 'cosinnus/widgets/filter_dropdown_widget.html'
    skip_empty_options = True
    
    def __init__(self, attrs=None, choices=()):
        super(DropdownChoiceWidget, self).__init__(attrs)

        self.choices = choices

    def value_from_datadict(self, data, files, name):
        value = super(DropdownChoiceWidget, self).value_from_datadict(data, files, name)
        self.data = data
        return value

    def render(self, name, value, attrs=None, choices=()):
        if not hasattr(self, 'data'):
            self.data = {}
        if value is None:
            value = ''
        
        final_attrs = self.build_attrs(attrs)
        render_options = self.compile_options(choices, [value], name)
        
        render_context = {
            'attrs': final_attrs,
            'options': render_options,
            'widget_id': 'DropdownChoiceWidget%s' % self.form_instance.fields[name].creation_counter,
            'label': self.form_instance.fields[name].label,
        }
        
        return render_to_string(self.template_name, render_context)

    def compile_options(self, choices, selected_choices, name):
        selected_choices = set(force_text(v) for v in selected_choices)
        render_options = []
        for option_value, option_label in chain(self.choices, choices):
            if not option_value and self.skip_empty_options:
                continue
            if isinstance(option_label, (list, tuple)):
                for option in option_label:
                    render_options.append(
                        self.compile_option(name, selected_choices, *option))
            else:
                render_options.append(
                    self.compile_option(name, selected_choices,
                                       option_value, option_label))
        return render_options

    def compile_option(self, name, selected_choices,
                      option_value, option_label):
        option_value = force_text(option_value)
        if option_label == BLANK_CHOICE_DASH[0][1]:
            option_label = _("All")
        data = self.data.copy()
        data[name] = option_value
        selected = data == self.data or option_value in selected_choices
        try:
            url = data.urlencode()
        except AttributeError:
            url = urlencode(data)
        return {
             'query_string': url,
             'label': force_text(option_label)
        }


