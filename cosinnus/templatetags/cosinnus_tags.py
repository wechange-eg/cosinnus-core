# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict

import six
from six.moves.urllib.parse import parse_qsl
from uuid import uuid1

from django import template
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import resolve, reverse
from django.http import HttpRequest
from django.template.defaulttags import URLNode, url as url_tag
from django.template.loader import render_to_string
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.core.registries import app_registry, attached_object_registry
from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.permissions import (check_ug_admin, check_ug_membership,
    check_ug_pending, check_object_write_access,
    check_group_create_objects_access, check_object_read_access)

register = template.Library()


@register.filter
def is_group_admin(user, group):
    """Template filter to check if the given user is an admin of the given
    group.

    .. seealso:: func:`cosinnus.utils.permissions.check_ug_admin`
    """
    return check_ug_admin(user, group)


@register.filter
def is_group_member(user, group):
    """Template filter to check if the given user is a member of the given
    group.

    .. seealso:: func:`cosinnus.utils.permissions.check_ug_membership`
    """
    return check_ug_membership(user, group)


@register.filter
def is_group_pending(user, group):
    """Template filter to check if the given user is a member of the given
    group.

    .. seealso:: func:`cosinnus.utils.permissions.check_ug_membership`
    """
    return check_ug_pending(user, group)

@register.filter
def has_read_access(user, obj):
    """
    Template filter to check if an object (either CosinnusGroup or BaseTaggableObject)
    is visibible to a user.
    This factors in all aspects of superusers and group memberships.
    """
    return check_object_read_access(obj, user)

@register.filter
def has_write_access(user, obj):
    """
    Template filter to check if a user can edit/update/delete an object 
    (either CosinnusGroup or BaseTaggableObject).
    If a CosinnusGroup is supplied, this will check if the user is a group admin or a site admin.
    This factors in all aspects of superusers and group memberships.
    """
    return check_object_write_access(obj, user)

@register.filter
def can_create_objects_in(user, group):
    """
    Template filter to check if a user can create objects in a CosinnusGroup.
    This factors in all aspects of superusers and group memberships.
    """
    return check_group_create_objects_access(group, user)

@register.filter
def can_create_groups(user):
    """
    Template filter to check if a user can create CosinnusGroups.
    """
    return user.is_authenticated()


@register.filter
def full_name(value):
    """Template filter to get a readable name for the given user

    .. code-block:: django

        {{ user|full_name }}

    :param AbstractBaseUser value: the user object
    :return: either the full user name or the login user name.
    """
    from django.contrib.auth.models import AbstractBaseUser
    if isinstance(value, AbstractBaseUser):
        return value.get_full_name() or value.get_username()
    return ""

@register.filter
def multiply(value, arg):
    """Template filter to multiply two numbers
    """
    return value * arg

@register.filter
def subtract(value, arg):
    """Template filter to multiply two numbers
    """
    return value - arg


@register.simple_tag(takes_context=True)
def cosinnus_menu(context, template="cosinnus/navbar.html"):
    if 'request' not in context:
        raise ImproperlyConfigured("Current request missing in rendering "
            "context. Include 'django.core.context_processors.request' in the "
            "TEMPLATE_CONTEXT_PROCESSORS.")

    request = context['request']
    user = request.user
    if user.is_authenticated():
        context['groups'] = CosinnusGroup.objects.get_for_user(request.user)

    current_app = resolve(request.path).app_name
    active_app = None
    active_app_name = None
    if 'group' in context:
        group = context['group']
        apps = []
        for app, name, label in app_registry.items():
            if app in settings.COSINNUS_HIDE_APPS:
                continue
            url = reverse('cosinnus:%s:index' % name, kwargs={'group': group.slug})
            if app == current_app:
                active_app = app
                active_app_name = name
            apps.append({
                'active': app == current_app,
                'label': label,
                'url': url,
                'app': app,
            })
        context.update({
            'apps': apps,
            'app_nav': True,
        })
    else:
        context['app_nav'] = False

    context.update({
        'active_app': active_app,
        'active_app_name': active_app_name,
    })
    return render_to_string(template, context)


@register.simple_tag(takes_context=True)
def cosinnus_render_attached_objects(context, source, filter=None):
    """
    Renders all attached files on a given source cosinnus object. This will
    collect and group all attached objects (`source.attached_objects`) by their
    model group and send them to the configured renderer for that model type
    (in each cosinnus app's `cosinnus_app.ATTACHABLE_OBJECT_RENDERERS`).

    :param source: the source object to check for attached objects
    :param filter: a comma seperated list of allowed Object types to be
        rendered. eg.: 'cosinnus_event.Event,cosinnus_file.FileEntry' will
        allow only Files and events to be rendered.
    """
    attached_objects = source.attached_objects.all()
    allowed_types = filter.replace(' ', '').split(',') if filter else []

    typed_objects = defaultdict(list)
    for att in attached_objects:
        attobj = att.target_object
        content_model = att.model_name
        if filter and content_model not in allowed_types:
            continue
        if attobj is not None:
            typed_objects[content_model].append(attobj)

    rendered_output = []
    for model_name, objects in six.iteritems(typed_objects):
        # find manager object for attached object type
        Renderer = attached_object_registry.get(model_name)  # Renderer is a class
        if Renderer:
            # pass the list to that manager and expect a rendered html string
            rendered_output.append(Renderer.render(context, objects))
        elif settings.DEBUG:
            rendered_output.append(_('<i>Renderer for %(model_name)s not found!</i>') % {
                'model_name': model_name
            })

    return ''.join(rendered_output)


@register.inclusion_tag('cosinnus/autocomplete.html')
def cosinnus_autocomplete(field, objects):
    return {
        'field': field,
        'objects': objects
    }


class URLNodeOptional(URLNode):
    """
    Exactly the same as `django.template.defaulttags.url` *except* `kwargs`
    needs to evaluate to `True`. All other `kwargs` are removed. This allows a
    bit more flexibility than the use of `{% url %}`.

    .. seealso:: http://code.djangoproject.com/ticket/9176
    """
    def render(self, context):
        self.kwargs = {k: v for k, v in six.iteritems(self.kwargs) if v.resolve(context)}
        return super(URLNodeOptional, self).render(context)


@register.tag
def url_optional(parser, token):
    """
    Creates the default `URLNode`, then routes it through the optional resolver
    with the same properties by first creating the `URLNode`. The parsing stays
    in Django core where it belongs.
    """
    urlnode = url_tag(parser, token)
    return URLNodeOptional(urlnode.view_name, urlnode.args, urlnode.kwargs,
        urlnode.asvar)
    
@register.tag(name='captureas')
def do_captureas(parser, token):
    """
        Captures block content into template variables.
        Source: https://djangosnippets.org/snippets/545/
        Usage:
            {% captureas label %}{% trans "Posteingang" %}{% if unread_count %} <strong>({{ unread_count }})</strong>{% endif %}{% endcaptureas %}
            {% include "cosinnus/leftnav_button.html" label=label  %}
    """
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("'captureas' node requires a variable name.")
    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()
    return CaptureasNode(nodelist, args)


class CaptureasNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.varname] = output
        return ""
    

@register.tag
def djajax_connect(parser, token):
    """
    """
    rest = []
    try:
        token_array = token.split_contents()
        tag_name, obj_prop, my_args = token_array[0], token_array[1], token_array[2:]
        obj, prop = obj_prop.split('.')
        print ">> obj, prop", obj, prop, my_args
    except ValueError:
        raise template.TemplateSyntaxError("'djajax_connect' requires a variable name.")
    
    return DjajaxConnectNode(obj, prop, my_args)


class DjajaxConnectNode(template.Node):
    
    # arguments the connect tag can take, and their defaults
    TAG_ARGUMENTS = {
        'trigger_on': 'value_changed',
        'post_to': '/api/v1/taggable_object/update/',
        'value_selector': 'val',
        'value_selector_arg': None,
        'value_object_property': None,
        'value_transform': None,
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
        additional_context = {}
        for arg_name, arg_default in DjajaxConnectNode.TAG_ARGUMENTS.items():
            self._addArgFromParams(self.my_args, additional_context, context, arg_name, arg_default)

        # get the wished id for the item, or generate one if not supplied
        node_id = '%s_%s_%d' % (self.obj, self.prop, uuid1())
        
        print ">>>> add context", additional_context
        
        djajax_entry = (context[self.obj], self.prop, node_id, additional_context)
        if not 'djajax_connect_list' in context:
            context.dicts[0]['djajax_connect_list'] = []
            #raise template.TemplateSyntaxError("Djajax not found in context. Have you inserted '{% djajax_setup %}' ?")
        context.dicts[0]['djajax_connect_list'].append(djajax_entry)
        
        return " djajax-id='%s' djajax-last-value='' " % (node_id) 


@register.tag
def djajax(parser, token):
    """
    """
    try:
        tag_name, directive = token.split_contents()
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
            
            ret = ''
            for obj, prop, node_id, additional_context in node_items:
                #ret += node_id + ' || '
                context = {
                    'node_id': node_id,
                    'app_label': obj.__class__.__module__.split('.')[0],
                    'model_name': obj.__class__.__name__,
                    'pk': obj.pk,
                    'property_name': prop,
                }
                #print ">>a aaaaa  aaaaad", additional_context
                context.update(additional_context)
                ret += render_to_string('cosinnus/js/djajax_connect.js', context) + '\n\n'
            
            return """<script type="text/javascript">\n%s\n</script>""" % ret
        else:
            raise template.TemplateSyntaxError("Djajax: Unknown directive '%s'." % self.directive)



@register.simple_tag(takes_context=True)
def strip_params(context, qs, *keys):
    """
    Given a URL query string (`foo=bar&lorem=ipsum`) and an arbitrary key /
    list of keys, strips those from the QS:
    """
    if isinstance(qs, six.string_types):
        parsed = dict(parse_qsl(qs))
    elif isinstance(qs, HttpRequest):
        from copy import copy
        parsed = copy(qs.GET.dict())
    else:
        parsed = {}
    for k in keys:
        parsed.pop(k, None)
    return urlencode(parsed)
