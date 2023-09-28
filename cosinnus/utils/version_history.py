from importlib import import_module
from operator import itemgetter

from dateutil import parser
from django.urls import reverse
from django.utils.text import slugify
from django.utils.timezone import now
from cosinnus import version_history


def _version_list(updates):
    """ Convert the UPDATES dict into a list (for sorting by datetime) and extend with additional information. """
    version_list = []
    version_history_url = reverse('cosinnus:version-history')
    for version, update in updates.items():
        # copy and extend update info
        version_details = update.copy()
        anchor = slugify(version)
        version_details.update({
            'version': version,
            'anchor': anchor,
            'url': f'{version_history_url}#{anchor}',
        })
        version_list.append(version_details)
    return version_list


def get_version_history():
    """ Return the full version history list for core and the portal. """
    versions = _version_list(version_history.UPDATES)

    portal_versions = None
    try:
        portal_version_history = import_module('apps.core.version_history')
        portal_versions = portal_version_history.UPDATES
    except ModuleNotFoundError:
        pass
    if portal_versions:
        versions += _version_list(portal_versions)

    versions = sorted(versions, key=itemgetter('datetime'), reverse=True)
    return versions


def get_version_history_for_user(user, limit=5):
    """ Return a limited version history list and the unread count for the user. Add a "read" flag to the versions.. """
    versions = get_version_history()
    unread_count = 0

    # mark and count unread versions for user
    if user.is_authenticated and hasattr(user, 'cosinnus_profile'):
        last_read_version_datetime = user.cosinnus_profile.settings.get('version_history_read_date')
        if last_read_version_datetime:
            last_read_version_datetime = parser.parse(last_read_version_datetime)
        for version in versions:
            if last_read_version_datetime and version.get('datetime') <= last_read_version_datetime:
                version['read'] = True
            else:
                version['read'] = False
                unread_count += 1

    # apply limit
    if limit:
        versions = versions[:limit]

    return versions, unread_count


def mark_version_history_as_read(user):
    """ Sets the version history read date for a user. """
    if hasattr(user, 'cosinnus_profile'):
        user.cosinnus_profile.settings['version_history_read_date'] = now()
        user.cosinnus_profile.save()