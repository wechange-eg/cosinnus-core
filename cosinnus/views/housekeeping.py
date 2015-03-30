# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.utils.dashboard import create_initial_group_widgets
from django.http.response import HttpResponse, HttpResponseForbidden
from django.contrib.auth import get_user_model
from django.db.models import Q
from cosinnus.views.profile import delete_userprofile
from cosinnus.utils.group import move_group_content as move_group_content_utils


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


def delete_spam_users(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    ret = ''
    user_csv = ''
    deleted_user_count = 0
    
    spam_users = get_user_model().objects.filter(date_joined__gt='2014-09-10').filter(
        Q(email__contains='.pl') | Q(cosinnus_profile__website__contains='.pl') | Q(email__contains='makre')
    ).distinct()
    
    
    for user in spam_users:
        user_groups = CosinnusGroup.objects.get_for_user(user)
        if len(user_groups) > 1:
            ret += '> Not deleting a user because he is in %d groups <br/>' % len(user_groups)
            continue
        
        breakadmin = False
        for group in user_groups:
            admins = CosinnusGroupMembership.objects.get_admins(group=group)
            if user.pk in admins:
                ret += '> Not deleting a user because he is admin in group %s' % group.slug
                breakadmin = True
                break
        if breakadmin:
            continue
        
        user_csv += '%(id)s,%(email)s,%(first_name)s,%(last_name)s<br/>' % user.__dict__
        deleted_user_count += 1
        if request.GET.get('commit', False) == 'true':
            delete_userprofile(user)
    
    if not request.GET.get('commit', False) == 'true':
        ret = ' **********   THIS IS A FAKE DELETION ONLY! user param ?commit=true to really delete the users! ***********'
    
    ret += '<br/><br/><br/>Deleted %d Users<br/><br/>' % deleted_user_count + user_csv
    return HttpResponse(ret)

def move_group_content(request, fromgroup, togroup):
    """ access to function for moving group content from one group to another """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Not authenticated')
    
    fromgroup = CosinnusGroup.objects.get_cached(slugs=fromgroup)
    togroup = CosinnusGroup.objects.get_cached(slugs=togroup)
    
    logs = move_group_content_utils(fromgroup, togroup)
    return HttpResponse("<br/>".join(logs))
        
        