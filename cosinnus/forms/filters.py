'''
Created on 04.08.2014

@author: Sascha 
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from itertools import chain
from django.template.loader import render_to_string
from django_filters.filters import ChoiceFilter
from django.core.exceptions import ImproperlyConfigured
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



class BaseChoiceWidget(forms.Widget):
    template_name = None
    skip_empty_options = False
    
    def __init__(self, attrs=None, choices=()):
        if not self.template_name:
            raise ImproperlyConfigured("You must provide a template_name for this widget!")
        super(BaseChoiceWidget, self).__init__(attrs)
        self.choices = choices

    def value_from_datadict(self, data, files, name):
        value = super(BaseChoiceWidget, self).value_from_datadict(data, files, name)
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
            'widget_id': 'FilterChoiceWidget%s' % self.form_instance.fields[name].creation_counter,
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
        else:
            option_label = self.format_label_value(option_label)
        data = self.data.copy()
        data[name] = option_value
        selected = data == self.data or option_value in selected_choices
        try:
            url = data.urlencode()
        except AttributeError:
            url = urlencode(data)
        return {
             'query_string': url,
             'label': option_label
        }
    
    def format_label_value(self, value):
        return force_text(value)


class DropdownChoiceWidget(BaseChoiceWidget):
    template_name = 'cosinnus/widgets/filter_dropdown_widget.html'
    skip_empty_options = True


class SelectUserWidget(BaseChoiceWidget):
    template_name = 'cosinnus/widgets/filter_user_select.html'
    
    def format_label_value(self, value):
        """ Show the user's full name """
        if not value:
            return _("Not assigned")
        elif (value.first_name or value.last_name):
            return "%s %s" % (value.first_name, value.last_name)
        return super(SelectUserWidget, self).format_label_value(value)
    

class AllObjectsFilter(ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct()
        qs = qs.order_by(self.name).values_list(self.name, flat=True)
        object_qs = getattr(self.model, self.name).field.rel.to._default_manager.filter(id__in=qs)
        self.extra['choices'] = [(o.id, o) for o in object_qs]
        if None in qs:
            self.extra['choices'].append((None, None))
        return super(AllObjectsFilter, self).field

