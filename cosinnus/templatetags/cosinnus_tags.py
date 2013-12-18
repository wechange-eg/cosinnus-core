# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict

import six

from django import template
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import resolve, reverse
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.core.loaders.apps import cosinnus_app_registry as car
from cosinnus.core.loaders.attached_objects import cosinnus_attached_object_registry as caor
from cosinnus.models import CosinnusGroup
from cosinnus.utils.permissions import (check_ug_admin, check_ug_membership,
    check_ug_pending)

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


@register.simple_tag(takes_context=True)
def cosinnus_menu(context, template="cosinnus/topmenu.html"):
    if not 'request' in context:
        raise ImproperlyConfigured("Current request missing in rendering "
            "context. Include 'django.core.context_processors.request' in the "
            "TEMPLATE_CONTEXT_PROCESSORS.")

    request = context['request']
    user = request.user
    if user.is_authenticated():
        context['groups'] = CosinnusGroup.objects.get_for_user(request.user)

    current_app = resolve(request.path).app_name
    if 'group' in context:
        group = context['group']
        apps = []
        for (app, name), label in zip(six.iteritems(car.app_names),
                                      six.itervalues(car.app_labels)):
            url = reverse('cosinnus:%s:index' % name, kwargs={'group': group.slug})
            apps.append({
                'active': app == current_app,
                'label': label,
                'url': url
            })
        context.update({
            'apps': apps,
            'app_nav': True,
        })
    else:
        context.update({'app_nav': False})
    return render_to_string(template, context)


@register.simple_tag(takes_context=True)
def cosinnus_render_attached_objects(context, source):
    """Renders all attached files on a given source cosinnus object. This will
    collect and group all attached objects (`source.attached_objects`) by their
    model group and send them to the configured renderer for that model type
    (in each cosinnus app's `cosinnus_app.ATTACHABLE_OBJECT_RENDERERS`).
    """
    attached_objects = source.attached_objects.all()

    typed_objects = defaultdict(list)
    for att in attached_objects:
        attobj = att.target_object
        content_model = att.model_name
        if attobj is not None:
            typed_objects[content_model].append(attobj)

    rendered_output = []
    for model_name, objects in six.iteritems(typed_objects):
        # find manager object for attached object type
        renderer = caor.attachable_object_renderers.get(model_name, None)
        if renderer:
            # pass the list to that manager and expect a rendered html string
            rendered_output.append(renderer.render_attached_objects(context, objects))
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
