# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import template
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string

from cosinnus.utils.permissions import check_ug_admin, check_ug_membership


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
def full_name(value):
    """Template filter to get a readable name for the given user

    .. code-block:: django+html

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
    from cosinnus.core.loaders.apps import cosinnus_app_registry as car
    if 'group' in context:
        group = context['group']
        apps = []
        for (app, name), label in zip(six.iteritems(car.app_names),
                                      six.itervalues(car.app_labels)):
            url = reverse('cosinnus:%s:index' % name, kwargs={'group': group.slug})
            apps.append({'label': label, 'url': url})
        context.update({
            'apps': apps,
            'app_nav': True,
        })
    else:
        context.update({'app_nav': False})
    return render_to_string(template, context)
