# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.models.group import CosinnusPortal


def exclude_special_folders(qs):
    """ Exclude in a queryset any FileEntry that is contained in a special folder (like attachments)
        Used so we don't show attached files in streams or widgets """
    special_folders = qs.model.objects.filter(group__portal=CosinnusPortal.get_current(), is_container=True).\
        exclude(special_type__isnull=True).exclude(special_type__exact='').values_list('path', flat=True)
    special_folders = list(set(special_folders))
    qs = qs.exclude(path__in=special_folders)
    return qs
