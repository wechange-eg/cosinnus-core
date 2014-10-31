# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid1

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.templatetags.static import static
from django.db.models.query import QuerySet
from django.core.serializers import serialize
from django.utils import simplejson

register = template.Library()



@register.tag
def djajax_connect(parser, token):
    """
    """
    try:
        token_array = token.split_contents()
        _, obj_prop, my_args = token_array[0], token_array[1], token_array[2:]
        obj, prop = obj_prop.rsplit('.', 1)
    except ValueError:
        raise template.TemplateSyntaxError("'djajax_connect' requires a variable name.")
    
    return DjajaxConnectNode(obj, prop, my_args)


class DjajaxConnectNode(template.Node):
    
    # arguments the connect tag can take, and their defaults
    TAG_ARGUMENTS = {
         # the jQuery trigger on which the value should be updated
        'trigger_on': 'value_changed',
        # the URL the value should be POSTed to
        'post_to': '/api/v1/taggable_object/update/',
        # which jQuery attribute selector do we get the value from the html element?
        'value_selector': 'val',
        # if the attribute selector isn't val (for example it's "attr", what's the attr argument?
        'value_selector_arg': None,
        # should the value be gotten from a DOM property instead of a jQuery select?
        'value_object_property': None,
        # a function that transforms the value read from the HTML element. it's return value is then POSTed
        'value_transform': None,
        # if this is set, ignore any data and always POST the supplied argument as data update
        'fixed_value': None,
        # do we allow sending empty data? if set to false, will not POST when the data is empty or ''
        'empty': 'true',
        # which JS function we should execute on successful POST execute
        'on_success': None,
        # which JS function args we should execute on successful POST execute
        'on_success_args': None,
        # which JS function we should execute on failed POST execute
        'on_error': None,
        # which JS function args should execute on failed POST execute
        'on_error_args': None,
    }
    
    def _addArgFromParams(self, add_from_args, add_to_dict, context, arg_name, default_value=None):
        """ Utility function to parse the argument list for a named argument, then 
            take the following argument as that arguments value (parse it either for strings or
            context reference) """
        arg_value = None
        for arg in self.my_args:
            if arg.startswith(arg_name + '='):
                arg_value = arg[len(arg_name)+1:]
        if not arg_value:
            if not default_value:
                return
            arg_value =  '"'+ default_value + '"'
        
        
        if arg_value[0] in ['"', "'"]:
            add_to_dict[arg_name] = arg_value[1:-1]
        else:
            add_to_dict[arg_name] = context[arg_value]
        
    
    def __init__(self, obj, prop, my_args):
        self.obj = obj
        self.prop = prop
        self.my_args = my_args

    def render(self, context):
        """ We're committing the crime of pushing variables to the bottom of the dict stack here... """
        # parse options
        extra_render = ''
        additional_context = {}
        for arg_name, arg_default in DjajaxConnectNode.TAG_ARGUMENTS.items():
            self._addArgFromParams(self.my_args, additional_context, context, arg_name, arg_default)
        
        # if we have gotten a fixed value data property, set it as data-value and configure 
        # to read out the data-value attribute
        if 'fixed_value' in additional_context:
            additional_context['value_selector'] = 'attr'
            additional_context['value_selector_arg'] = 'data-value'
            extra_render += 'data-value="%s"' % additional_context['fixed_value']
            del additional_context['fixed_value']
        
        if '.' in self.obj:
            obj, properties = self.obj.split('.', 1)
            resolved_obj = context[obj]
            for sub_property in properties.split('.'):
                resolved_obj = getattr(resolved_obj, sub_property)
        else:
            resolved_obj = context[self.obj]
            
        # get the wished id for the item, or generate one if not supplied
        node_id = '%s_%s_%d' % (self.obj.replace('.','_'), self.prop, uuid1())
        
            
        djajax_entry = (resolved_obj, self.prop, node_id, additional_context)
        if not 'djajax_connect_list' in context:
            context.dicts[0]['djajax_connect_list'] = []
            #raise template.TemplateSyntaxError("Djajax not found in context. Have you inserted '{% djajax_setup %}' ?")
        context.dicts[0]['djajax_connect_list'].append(djajax_entry)
        
        return " djajax-id='%s' djajax-last-value='' %s " % (node_id, extra_render) 


@register.tag
def djajax(parser, token):
    """
    """
    try:
        _, directive = token.split_contents()
    except ValueError:
        directive = 'generate'
    
    return DjajaxSetupNode(directive)


class DjajaxSetupNode(template.Node):
    def __init__(self, directive='init'):
        self.directive = directive
    
    def render(self, context):
        if self.directive == 'generate':
            #import ipdb; ipdb.set_trace();
            node_items = context.get('djajax_connect_list', [])
            if not node_items:
                return ''
            
            rendered_js = ''
            context_items = []
            for obj, prop, node_id, additional_context in node_items:
                #rendered_js += node_id + ' || '
                context = {
                    'node_id': node_id,
                    'app_label': obj.__class__.__module__.split('.')[0],
                    'model_name': obj.__class__.__name__,
                    'pk': obj.pk,
                    'property_name': prop,
                }
                context.update(additional_context)
                context_items.append(context)
                
            rendered_js += render_to_string('cosinnus/js/djajax_connect.js', {'djajax_items': context_items}) + '\n'
            
            js_file = static('js/djajax.js')
            return """<script src="%s"></script>\n<script type="text/javascript">\n%s\n</script>""" % (js_file, rendered_js)
        else:
            raise template.TemplateSyntaxError("Djajax: Unknown directive '%s'." % self.directive)

@register.filter
def jsonify(obj):
    """
    Returns JSON output for an object
    """
    if isinstance(obj, QuerySet):
        ret = serialize('json', obj)
    else:
        ret = simplejson.dumps(obj)
    return mark_safe(ret)

