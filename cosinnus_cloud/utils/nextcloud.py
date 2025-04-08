import json
import logging
import secrets
import string
import urllib
from typing import List, Mapping, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from oauth2_provider.models import Application

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus_cloud.models import CloudFile, SimpleCloudFile
from cosinnus_cloud.utils.text import utf8_encode

logger = logging.getLogger('cosinnus')

_session = requests.Session()


class OCSResponse:
    def __init__(self, json):
        self.json = json

    @property
    def status(self) -> str:
        return self.json['ocs']['meta']['status']

    @property
    def statuscode(self) -> int:
        return int(self.json['ocs']['meta']['statuscode'])

    @property
    def message(self) -> str:
        return self.json['ocs']['meta']['message']

    @property
    def data(self) -> Mapping[str, object]:
        return self.json['ocs']['data']

    @property
    def ok(self):
        """True iff the status is 'ok'"""
        return self.status == 'ok'

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f'<OCSResponse status={self.status} statuscode={self.statuscode} data={self.data}>'

    def __str__(self):
        return str(self.json)


class OCSException(RuntimeError):
    def __init__(self, statuscode, message):
        self.message = message
        self.statuscode = statuscode

    def __repr__(self):
        return f'OCSException({self.statuscode}, {self.message!r})'

    def __str__(self):
        return f'Statuscode {self.statuscode} ({self.message})'


HEADERS = {'OCS-APIRequest': 'true', 'Accept': 'application/json'}
WEBDAV_HEADERS = {'Content-Type': 'text/xml'}


def _response_or_raise(requests_response: requests.Response):
    if not requests_response.ok:
        logger.error(
            'Got HTTP result %s from nextcloud, text: %s',
            requests_response,
            requests_response.text,
        )
        requests_response.raise_for_status()
    try:
        response_json = requests_response.json()
    except Exception:
        raise OCSException(-1, requests_response.text)
    response = OCSResponse(response_json)
    if response.ok:
        return response
    else:
        raise OCSException(response.statuscode, response.message)


def _webdav_response_or_raise(requests_response: requests.Response):
    if not requests_response.ok:
        logger.error(
            'Got Webdav HTTP result %s from nextcloud, text: %s',
            requests_response,
            requests_response.text,
        )
        requests_response.raise_for_status()
    return requests_response.text


def create_user(userid: str, display_name: str, email: str) -> OCSResponse:
    # We don't want the user to receive an email asking the user to set a password, as the
    # login will be done via OAuth, so we just set a random password
    random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

    data = {
        'userid': userid,
        'displayName': display_name,
        'email': email,
        'password': random_password,
    }
    res = requests.post(
        f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users',
        auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        headers=HEADERS,
        data=data,
    )
    return _response_or_raise(res)


def update_user_email(userid: str, email: str) -> OCSResponse:
    data = {
        'key': 'email',
        'value': email,
    }
    return _response_or_raise(
        requests.put(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{quote(userid)}',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=HEADERS,
            data=data,
        )
    )


def update_user_name(userid: str, display_name: str) -> OCSResponse:
    data = {
        'key': 'displayname',
        'value': display_name,
    }
    return _response_or_raise(
        requests.put(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{quote(userid)}',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=HEADERS,
            data=data,
        )
    )


def disable_user(userid: str) -> OCSResponse:
    return _response_or_raise(
        requests.put(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{quote(userid)}/disable',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=HEADERS,
        )
    )


def enable_user(userid: str) -> OCSResponse:
    return _response_or_raise(
        requests.put(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{quote(userid)}/enable',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=HEADERS,
        )
    )


def delete_user(userid: str) -> OCSResponse:
    return _response_or_raise(
        requests.delete(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{quote(userid)}',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=HEADERS,
        )
    )


def add_user_to_group(userid: str, groupid: str) -> OCSResponse:
    return _response_or_raise(
        requests.post(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{quote(userid)}/groups',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=HEADERS,
            data={'groupid': groupid},
        )
    )


def remove_user_from_group(userid: str, groupid: str) -> OCSResponse:
    return _response_or_raise(
        requests.delete(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users/{quote(userid)}/groups',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=HEADERS,
            data={'groupid': groupid},
        )
    )


def add_user_to_admin_group(userid: str) -> OCSResponse:
    return add_user_to_group(userid, 'admin')


def remove_user_from_admin_group(userid: str) -> OCSResponse:
    return remove_user_from_group(userid, 'admin')


def create_group(groupid: str) -> Optional[OCSResponse]:
    try:
        return _response_or_raise(
            requests.post(
                f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/groups',
                auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
                headers=HEADERS,
                data={'groupid': groupid},
            )
        )
    except OCSException as e:
        if e.statuscode == 102:
            logger.info('group [%s] already exists, doing nothing', groupid)
            return None
        raise


def delete_group(groupid: str) -> Optional[OCSResponse]:
    try:
        return _response_or_raise(
            requests.delete(
                f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/groups/{groupid}',
                auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
                headers=HEADERS,
            )
        )
    except OCSException:
        raise


def create_group_folder(name: str, group_id: str, group, raise_on_existing_name=True) -> Optional[OCSResponse]:
    """Creates a nextcloud groupfolder for the given group, sets its quota, and returns its
    nextcloud DB id."""
    # First, check whether the name is already taken (workaround for bug in groupfolders)
    response = _response_or_raise(
        requests.get(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        )
    )

    # if a group folder with that name exists already in the NC, do nothing, as this is already our target folder
    same_name_entries = (
        [] if not response.data else [folder for folder in response.data.values() if folder['mount_point'] == name]
    )
    if len(same_name_entries) > 0:
        # we do however, check if the folder id is set in the cosinnus group!
        if not group.nextcloud_groupfolder_id:
            logger.info('Group had its nextcloud groupfolder id missing - corrected it with matched folder!')
            group.nextcloud_groupfolder_id = int(same_name_entries[0].get('id'))
            group.save()

        if raise_on_existing_name:
            raise ValueError('A groupfolder with that name already exists')
        else:
            logger.info('group folder [%s] already exists, doing nothing', name)
            # doing nothing except making sure the group has access to the folder
            add_group_access_for_folder(group_id, group.nextcloud_groupfolder_id)
            return

    # create groupfolder
    response = _response_or_raise(
        requests.post(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            data={'mountpoint': name},
        )
    )

    # save the groupfolder id (not the name,
    # that has been saved at group id generation time in `generate_group_nextcloud_groupfolder_name`)
    folder_id = response.data['id']
    if folder_id:
        group.nextcloud_groupfolder_id = int(folder_id)
        group.save()
    else:
        logger.error(
            'Nextcloud folder creation did not return a folder id!',
            extra={
                'group': group,
                'folder_id': folder_id,
            },
        )

    # assign our group access to the groupfolder
    add_group_access_for_folder(group_id, folder_id)

    # set the quota for the group folder, in bytes, unless the quota is the
    # default (-3 for "unlimited")
    if (
        settings.COSINNUS_CLOUD_NEXTCLOUD_GROUPFOLDER_QUOTA
        and settings.COSINNUS_CLOUD_NEXTCLOUD_GROUPFOLDER_QUOTA != -3
    ):
        latest_response = _response_or_raise(
            requests.post(
                f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders/{folder_id}/quota',
                headers=HEADERS,
                auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
                data={'quota': settings.COSINNUS_CLOUD_NEXTCLOUD_GROUPFOLDER_QUOTA},
            )
        )

    return latest_response


def rename_group_folder(folder_id: int, new_name: str):
    """Renames a group folder for a given id (int)"""
    response = _response_or_raise(
        requests.post(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders/{folder_id}/mountpoint',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            data={'mountpoint': new_name},
        )
    )
    return response.data and response.data.get('success', False) is True


def set_group_display_name(group_id: str, new_name: str):
    """Set the display name for a group."""
    response = _response_or_raise(
        requests.put(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v2.php/cloud/groups/{group_id}',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            data={'key': 'displayname', 'value': new_name},
        )
    )
    return response.data and response.data.get('success', False) is True


def get_groupfolder_name(folder_id: int):
    """Retrieves a group folder name for a given id (int)"""
    response = _response_or_raise(
        requests.get(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders/{folder_id}',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        )
    )
    return response.data and response.data.get('mount_point', None) or None


def add_group_access_for_folder(group_id: str, folder_id: int) -> bool:
    """Adds a nextcloud group's access to a group folder.
    Returns True if successful"""
    # assign our group access to the groupfolder
    response = _response_or_raise(
        requests.post(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders/{folder_id}/groups',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            data={'group': group_id},
        )
    )
    return response.data and response.data.get('success', False) is True


def remove_group_access_for_folder(group_id: str, folder_id: int) -> bool:
    """Removes a nextcloud group's access to a group folder.
    Returns True if successful"""
    # take away our group's access to the groupfolder
    response = _response_or_raise(
        requests.delete(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders/{folder_id}/groups/{group_id}',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        )
    )
    return response.data and response.data.get('success', False) is True


def delete_groupfolder(folder_id: int) -> bool:
    """Deletes a nextcloud group folder.
    Returns True if successful"""
    response = _response_or_raise(
        requests.delete(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/groupfolders/folders/{folder_id}',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        )
    )
    return response.data and response.data.get('success', False) is True


def files_search(
    folder_name=None,
    timeout=settings.COSINNUS_CLOUD_NEXTCLOUD_REQUEST_TIMEOUT,
    order_by_last_modified=False,
):
    """Webdav request that lists all files in order by last modified date for all files from the root of
    the admin user, or from a specified folder.
    @param order_by_last_modified:  should the webdav API sort results by last modified?
        if True, results will be sorted by the actual last modified date, which includes
            files' actual timestampt. so recently uploaded old files will not show as new!
        if False, defaults to id ordering, which makes a nice "newest files" list, but
            ignores changes and edits to documents"""
    url = f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/remote.php/dav/'

    folder_term = ''
    if folder_name:
        folder_term = f'{folder_name}/'

    order_term = ''
    if order_by_last_modified:
        order_term = """\
<d:orderby>
    <d:order>
        <d:prop>
            <d:getlastmodified/>
        </d:prop>
        <d:ascending/>
    </d:order>
</d:orderby>"""

    body = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<d:searchrequest xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns" xmlns:nc="http://nextcloud.org/ns">
    <d:basicsearch>
        <d:select>
            <d:prop>
                <d:displayname/>
                <oc:fileid/>
            </d:prop>
        </d:select>
        <d:from>
            <d:scope>
                <d:href>/files/{settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME}/{folder_term}</d:href>
                <d:depth>infinity</d:depth>
            </d:scope>
        </d:from>
        <d:where>
            <d:gte>
                <d:prop>
                    <oc:size/>
                </d:prop>
                <d:literal>0</d:literal>
            </d:gte>
        </d:where>
        {order_term}
    </d:basicsearch>
</d:searchrequest>"""
    return _webdav_response_or_raise(
        requests.request(
            method='SEARCH',
            url=url,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=WEBDAV_HEADERS,
            timeout=timeout,
            data=utf8_encode(body),
        )
    )


def list_group_folder_files(groupfolder_name, user=None):
    """Returns a list of `CloudFile`s for a given nextcloud GroupFolder id"""
    try:
        response_text = files_search(groupfolder_name)
    except Exception:
        return []
    file_list = parse_cloud_files_search_response(response_text, user=user)
    return file_list


def list_all_users():
    """Returns a list of all user ids currently existing in nextcloud"""
    response = _response_or_raise(
        requests.get(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/ocs/v1.php/cloud/users',
            headers=HEADERS,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        )
    )
    if response.data and 'users' in response.data:
        return response.data['users']
    return []


def parse_cloud_files_search_response(response_text, path_filter=None, user=None):
    """Parses a Webdav endpoint response text into a list of `CloudFile`s
    @param response_text: The requests's response.text
    @param path_filter: If given, a function with path as argument that has to
        be truthy for each given file to be included in the results
    @param user: If given, attaches the user as "owner" of each of the files
    """

    soup = BeautifulSoup(response_text, 'xml')
    content = soup.find('d:multistatus')
    if not content:
        return []

    cloud_file_list = []
    all_responses = content.find_all('d:response')
    # since nextcloud seemingly ignores the last-modified sorting, reverse the list,
    # at least then it is sorted by IDs (last created)
    all_responses = reversed(all_responses)
    for search_result in all_responses:
        filepath = search_result.find('d:href').get_text()
        if filepath:
            if filepath.endswith('/'):
                continue  # result is a folder
            splits = filepath.split('/')
            id_pointer = search_result.find('oc:fileid')
            file_id = id_pointer and id_pointer.get_text() or None
            filename = urllib.parse.unquote(splits[-1])
            folder_name = urllib.parse.unquote(splits[-2])
            actual_path = filepath.split(f'/dav/files/{settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME}')[1]
            if path_filter is not None and not path_filter(actual_path):
                continue  # result did not match the path filter
            root_folder_name = urllib.parse.unquote(actual_path.split('/')[1])  # starts with '/', so take 2nd item

            cloud_file_list.append(
                CloudFile(
                    title=filename,
                    url=get_permalink_for_file_id(file_id) if file_id else None,
                    download_url=f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}{filepath}',
                    type=None,
                    folder=folder_name,
                    root_folder=root_folder_name,
                    path=actual_path,
                    user=user,
                )
            )
    return cloud_file_list


def _get_requesttoken_for_session(session, get_url):
    """Gets a Nextcloud CSRF requesttoken for a requests Session"""
    get_response = session.get(
        f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}{get_url}',
        headers=HEADERS,
        auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
    )
    if not get_response.status_code == 200:
        raise Exception('Nextcloud admin  login request did not return status code 200! %s' % get_response.text)
    soup = BeautifulSoup(get_response.text, 'xml')
    try:
        requesttoken = soup.find('head').attrs.get('data-requesttoken')
    except Exception:
        raise Exception("'data-requesttoken' was not found in <head> tag of Nextcloud admin page!")
    return requesttoken


def create_social_login_apps():
    """Creates a Nextcloud sociallogin client app, and then creates a corresponding django oauth toolkit
    provider app using the same client id and secret. Both apps will be given the proper URL paths.
    This is safe to call multiple times, although subsequent calls will generate and use a different
    client id and secret.
    @return: True if all apps were created/updated successfully, raises otherwise"""

    portal_domain = CosinnusPortal.get_current().get_domain()
    client_id = secrets.token_urlsafe(16)
    client_secret = secrets.token_urlsafe(16)
    nextcloud_app_name = 'wechange'
    wechange_app_name = 'nextcloud'

    with requests.Session() as session:
        requesttoken = _get_requesttoken_for_session(session, '/settings/admin/sociallogin')
        # social login app form data
        # Note: used to be provider_arg = "custom_oauth2_providers[0][%s]" in a previous version
        provider_arg_modern = 'custom_providers[custom_oauth2][0][%s]'
        # we send both formats of arguments, as it is safe, to support both versions of sociallogin
        provider_arg_legacy = 'custom_oauth2_providers[0][%s]'
        data = {}
        for provider_arg in [provider_arg_modern, provider_arg_legacy]:
            # at least one providers/options array entry must be given!
            data.update(
                {
                    'update_profile_on_login': 1,  # legacy options format
                    'options[update_profile_on_login]': 1,  # v24 format, one of this array is needed!
                    'providers[twitter][appid]': '',  # v24 format, one of this array is needed!
                    provider_arg % 'name': nextcloud_app_name,
                    provider_arg % 'title': nextcloud_app_name,
                    provider_arg % 'apiBaseUrl': f'{portal_domain}/o',
                    provider_arg % 'authorizeUrl': f'{portal_domain}/o/authorize/',
                    provider_arg % 'tokenUrl': f'{portal_domain}/o/token/',
                    provider_arg % 'profileUrl': f'{portal_domain}/group/forum/cloud/oauth2/',
                    provider_arg % 'logoutUrl': f'{portal_domain}/logout/',
                    provider_arg % 'clientId': client_id,
                    provider_arg % 'clientSecret': client_secret,
                    provider_arg % 'scope': 'read',
                    provider_arg % 'profileFields': '',
                    provider_arg % 'groupsClaim': '',
                    provider_arg % 'style': '',
                    provider_arg % 'defaultGroup': '',
                    provider_arg % 'tg_bot': None,
                    provider_arg % 'tg_token': None,
                    provider_arg % 'tg_group': None,
                }
            )
        session_headers = dict(HEADERS)
        session_headers['requesttoken'] = requesttoken

        # create social login app
        post_response = session.post(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/sociallogin/settings/save-admin',
            headers=session_headers,
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            data=data,
        )
        if not post_response.status_code == 200:
            raise Exception(
                'Nextcloud admin sociallogin save request did not return status code 200! %s' % post_response.text
            )

    # create django oauth toolkit provider app
    portal_id = CosinnusPortal.get_current().id
    app, __ = Application.objects.get_or_create(name=f'{wechange_app_name}{portal_id}')
    app.client_id = client_id
    app.client_secret = client_secret
    app.redirect_uris = f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/sociallogin/custom_oauth2/{nextcloud_app_name}'
    app.client_type = Application.CLIENT_PUBLIC
    app.authorization_grant_type = Application.GRANT_AUTHORIZATION_CODE
    app.skip_authorization = True
    app.save()

    return True


def _make_ocs_call(relative_url, post_data={}, headers=HEADERS, session=None, print_to_console=False):
    """Fires a (blocking) OCS POST to a given URL with given POST data.
    @param relative_url: relative API endpoint URL, without domain, with leading slash
    @return: True if successful, False if not."""
    try:
        client = session or _session
        if print_to_console:
            print(f'Applying setting > {relative_url} -> {post_data}... ', end='')
        response = client.post(
            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}{relative_url}',
            auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
            headers=headers,
            json=post_data,
        )
        if print_to_console:
            print(response.status_code)
        return response.status_code == 200
    except OCSException as e:
        message = (
            f'Nextcloud OCS POST call to "{relative_url}" with data {post_data} was not successful. '
            f'Status code: {e.statuscode}'
        )
        if print_to_console:
            print(message)
        else:
            logger.warn(message)
        return False


def apply_nextcloud_settings(print_to_console=False):
    """
    Applies configured settings from conf `COSINNUS_CLOUD_NEXTCLOUD_SETTINGS` via OCS
    DEPRECATED: now handled by Ansible.
    """

    # default user quota
    _make_ocs_call(
        '/ocs/v2.php/apps/provisioning_api/api/v1/config/apps/files/default_quota',
        {'value': settings.COSINNUS_CLOUD_NEXTCLOUD_SETTINGS['DEFAULT_USER_QUOTA']},
        print_to_console=print_to_console,
    )
    # disable public upload
    _make_ocs_call(
        '/ocs/v2.php/apps/provisioning_api/api/v1/config/apps/core/shareapi_allow_public_upload',
        {'value': settings.COSINNUS_CLOUD_NEXTCLOUD_SETTINGS['ALLOW_PUBLIC_UPLOADS']},
        print_to_console=print_to_console,
    )
    # disable autocomplete for users
    _make_ocs_call(
        '/ocs/v2.php/apps/provisioning_api/api/v1/config/apps/core/shareapi_allow_share_dialog_user_enumeration',
        {'value': settings.COSINNUS_CLOUD_NEXTCLOUD_SETTINGS['ALLOW_AUTOCOMPLETE_USERS']},
        print_to_console=print_to_console,
    )
    # send email to new users
    _make_ocs_call(
        '/settings/users/preferences/newUser.sendEmail',
        {'value': settings.COSINNUS_CLOUD_NEXTCLOUD_SETTINGS['SEND_EMAIL_TO_NEW_USERS']},
        print_to_console=print_to_console,
    )

    # --- Apps Session ---
    with requests.Session() as session:
        requesttoken = _get_requesttoken_for_session(session, '/settings/apps')
        session_headers = dict(HEADERS)
        session_headers['requesttoken'] = requesttoken

        # enable apps
        _make_ocs_call(
            '/settings/apps/enable',
            {
                'appIds': settings.COSINNUS_CLOUD_NEXTCLOUD_SETTINGS['ENABLE_APP_IDS'],
                'groups': [],
            },
            headers=session_headers,
            session=session,
            print_to_console=print_to_console,
        )
        # disable apps
        _make_ocs_call(
            '/settings/apps/disable',
            {'appIds': settings.COSINNUS_CLOUD_NEXTCLOUD_SETTINGS['DISABLE_APP_IDS']},
            headers=session_headers,
            session=session,
            print_to_console=print_to_console,
        )

    # onlyoffice settings (TODO)
    # https://nextcloud.staging.wechange.de/apps/onlyoffice/ajax/settings/address
    # put request!!
    """
    documentserver: https://onlyoffice.<domain>/
    documentserverInternal: http://oo-ds/
    storageUrl: https://nextcloud.<domain>/
    secret:
    demo: false
    """


def perform_fulltext_search(userid: str, query: str, page=1, page_size=20, *, session=None):
    """
    Perform a fulltext file search as the given user and return the result.
    Requires the fulltextsearch_admin-api addon to be installed on the Nextcloud server.
    To make the search query behave like Haystack does ("foo bar" searches for "foo" AND "bar", instead of "foo"
    OR "bar"), query words are prepended with a plus.
    """

    anded_query = ' '.join(f'+{word}' for word in query.split(' '))

    search_request = {
        'author': userid,
        'providers': 'files',
        'search': anded_query,
        'page': page,
        'size': page_size,
        # "options": {
        #     "files_within_dir": "",
        #     "files_local": "",
        #     "files_external": "",
        #     "files_group_folder": "",
        #     "files_extension": "",
        # }
    }

    client = session or _session

    response = client.get(
        f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/fulltextsearch_admin-api/v1/remote',
        auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        headers=HEADERS,
        params={'request': json.dumps(search_request)},
    )

    response.raise_for_status()

    return response.json()['result'][0]


def find_files(
    userid: str,
    folder: str = '',
    name_query: str = None,
    page=1,
    page_size=5,
    also_search_content=False,
    search_options=None,
    *,
    session=None,
):
    """
    Finds files by name, unlike "perform_fulltext_search", by default, this function does only search in the filename,
    not the content
    """

    options = {
        'files_within_dir': folder,
        # "files_local": "",
        # "files_external": "",
        # "files_group_folder": "",
        # "files_extension": "",
    }

    if not also_search_content:
        options['search_only'] = ['title']

    options.update(search_options or {})

    search_request = {
        'author': userid,
        'providers': 'files',
        'page': page,
        'size': page_size,
        'options': options,
    }

    if name_query and name_query.strip():
        name_query = name_query.strip()
        search_request['search'] = ' '.join(f'+{word}' for word in name_query.split(' '))
    else:
        search_request['empty_search'] = True

    client = session or _session

    response = client.get(
        f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/fulltextsearch_admin-api/v1/remote',
        auth=settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH,
        headers=HEADERS,
        params={'request': json.dumps(search_request)},
    )

    response.raise_for_status()
    return response.json()['result'][0]


def find_newest_files(
    userid: str,
    folder: str = '',
    name_query: str = None,
    page=1,
    page_size=5,
    also_search_content=False,
    *,
    session=None,
):
    return find_files(
        userid=userid,
        folder=folder,
        name_query=name_query,
        page=page,
        page_size=page_size,
        also_search_content=also_search_content,
        search_options={'sort': [{'mtime': {'order': 'desc', 'unmapped_type': 'long'}}]},
        session=session,
    )


def get_groupfiles_match_list(
    userid: str,
    folder: str = '',
    name_query: str = None,
    page=1,
    page_size=10,
    *,
    session=None,
) -> List[SimpleCloudFile]:
    """Convenience function that calls "find_newest_files" and returns a SimpleCloudFile object."""

    results = find_newest_files(
        userid=userid,
        folder=folder,
        name_query=name_query,
        page=page,
        page_size=page_size,
        session=session,
    )
    return [
        SimpleCloudFile(id=int(doc['id']), filename=doc['info']['file'], dirname=doc['info']['path'])
        for doc in results['documents']
    ]


def get_permalink_for_file_id(id: int):
    return f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/f/{id}'
