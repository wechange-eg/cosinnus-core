# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.dashboard import create_initial_group_widgets
from django.http.response import HttpResponse, HttpResponseForbidden


def housekeeping(request):
    """ Do some integrity checks and corrections. 
        Currently doing:
            - Checking all groups and projects for missing widgets versus the default widget
                settings and adding missing widgets
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    groups = CosinnusGroup.objects.all()
    ret = ""
    for group in groups:
        ret += "Checked group %s\n<br/>" % group.slug
        create_initial_group_widgets(None, group)
    return HttpResponse(ret)
