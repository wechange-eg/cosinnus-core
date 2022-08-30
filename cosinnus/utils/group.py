# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

from urllib.parse import quote as urlquote

from django.apps import apps
from django.db.models import Q, Count
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text


from cosinnus.conf import settings
from functools import lru_cache


DEFAULT_CONTENT_MODELS = [
    'cosinnus_note.Note', 
    'cosinnus_file.FileEntry',
    'cosinnus_event.Event',
    'cosinnus_poll.Poll',
    'cosinnus_marketplace.Offer',
    'cosinnus_todo.TodoEntry',
    'cosinnus_etherpad.Etherpad'
]

def move_group_content(from_group, to_group, models=None, verbose=False):
    """ Moves all BaseTaggableObject content from one CosinnusGroup to another. """
    if not models:
        models = DEFAULT_CONTENT_MODELS
    
    actions_done = []
    for model_str in models:
        app_label, model = model_str.split('.')
        model_cls = apps.get_model(app_label, model)
        for obj in model_cls.objects.filter(group=from_group):
            obj.group = to_group
            obj.save()
            s = "moved '%d' %s: from group %d to group %d" % (obj.id, model_str, from_group.id, to_group.id)
            if verbose:
                print(s)
            actions_done.append(s)
    return actions_done


_CosinnusGroup = None

def get_cosinnus_group_model():
    """
    Return the cosinnus tag object model that is defined in
    :data:`settings.COSINNUS_TAG_OBJECT_MODEL`
    
    Also we cache the CosinnusGroupModel to save calling django internals forever.
    """
    global _CosinnusGroup
    if _CosinnusGroup is None:
        from django.core.exceptions import ImproperlyConfigured
        from cosinnus.conf import settings
    
        try:
            app_label, model_name = settings.COSINNUS_GROUP_OBJECT_MODEL.split('.')
        except ValueError:
            raise ImproperlyConfigured("COSINNUS_GROUP_OBJECT_MODEL must be of the form 'app_label.model_name'")
        #tag_model = get_model(app_label, model_name)
        group_model = apps.get_model(app_label=app_label, model_name=model_name)
        if group_model is None:
            raise ImproperlyConfigured("COSINNUS_GROUP_OBJECT_MODEL refers to model '%s' that has not been installed" %
                settings.COSINNUS_TAG_OBJECT_MODEL)
        _CosinnusGroup = group_model
        
    return _CosinnusGroup   


def message_group_admins_url(group, group_admins=None):
    """ Generates a postman:write URL to the admins of the given group, complete with subject line """
    group_admins = group_admins or group.actual_admins
    if not group_admins:
        return None
    message_subject = force_text(_('Question about')) + ' ' + force_text(_('Group') if group.type == group.TYPE_SOCIETY else _('Project')) + ': ' + group.name
    return reverse('postman:write', kwargs={'recipients':','.join([user.username for user in group_admins])}) + '?subject=' + urlquote(message_subject)


def get_default_user_group_slugs():
    """ Returns the slugs of the default user groups, that every user gets placed in on registering. """
    return getattr(settings, 'NEWW_DEFAULT_USER_GROUPS', [])


@lru_cache(maxsize=None)
def get_default_user_group_ids():
    """ Returns the ids of the default user groups, that every user gets placed in on registering. """
    default_user_groups = get_cosinnus_group_model().objects.filter(slug__in=get_default_user_group_slugs())
    return list(default_user_groups.values_list('id', flat=True))


def get_group_query_filter_for_search_terms(terms):
    """ Returns a django Q filter for use on GROUP_MODEL that returns all projects/groups with matching
        names, given an array of search terms. Each search term needs to be matched (AND)
        on at least one of the groups'/projects' name fields (OR). Case is insensitive.
        @param terms: An array of string search terms.
        @return: A django Q object.
    """
    first_term, other_terms = terms[0], terms[1:]

    q = Q(name__icontains=terms[0])
    for other_term in other_terms:
        add_q = Q(name__icontains=other_term)
        q &= add_q

    return q


def prioritize_suggestions_output(request, users):
    from cosinnus.models.group import CosinnusGroupMembership
    from cosinnus.models.membership import MEMBER_STATUS

    """
    Returns a QS of users with the number of group/project/conferences connections in relation to `request.user`.
    @param request: request to get the request.user
    @return: A django QS
    """
    current_user_groups_ids = CosinnusGroupMembership.objects.filter(group__is_active=True).filter(status__in=MEMBER_STATUS).filter(user=request.user).values_list('group_id', flat=True)
    users = users.annotate(matching_memberships=Count('cosinnus_memberships', filter=Q(cosinnus_memberships__status__in=MEMBER_STATUS, cosinnus_memberships__group_id__in=current_user_groups_ids))) 
    users = users.order_by('-matching_memberships', 'first_name')
    return users
