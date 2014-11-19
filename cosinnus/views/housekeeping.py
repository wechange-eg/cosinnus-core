# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.dashboard import create_initial_group_widgets
from django.http.response import HttpResponse

def housekeeping(request):
    groups = CosinnusGroup.objects.all()
    ret = ""
    for group in groups:
        ret += "Checked group %s\n<br/>" % group.slug
        create_initial_group_widgets(None, group)
    return HttpResponse(ret)
