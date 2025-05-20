import logging

import requests

from cosinnus.conf import settings

logger = logging.getLogger(__name__)


class DeckConnectionException(Exception):
    """Exception raised when a dock api call failed."""

    pass


class DeckConnection:
    BASE_URL = f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/index.php/apps/deck'
    HEADERS = {'OCS-APIRequest': 'true', 'Accept': 'application/json'}
    API_PARAMS = {'auth': settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH, 'headers': HEADERS}

    def _api_get(self, url):
        """API GET wrapper."""
        return requests.get(self.BASE_URL + url, **self.API_PARAMS)

    def _api_post(self, url, data):
        """API POST wrapper."""
        return requests.post(self.BASE_URL + url, json=data, **self.API_PARAMS)

    def _api_put(self, url, data):
        """API PUT wrapper."""
        return requests.put(self.BASE_URL + url, json=data, **self.API_PARAMS)

    def _api_delete(self, url):
        """API DELETE wrapper."""
        return requests.delete(self.BASE_URL + url, **self.API_PARAMS)

    def _is_deck_app_active_for_group(self, group):
        """Check if the deck app activated in a group."""
        return 'cosinnus_deck' not in group.get_deactivated_apps()

    def group_board_create(self, group):
        """Creates a Deck board for a group and adds the group permissions to it."""
        if not group.nextcloud_group_id:
            # Nextcloud group id is required to create a group board.
            return
        if group.nextcloud_deck_board_id:
            # Group already has a deck board created.
            return
        data = {'title': group.name, 'color': 'ffffff'}
        response = self._api_post('/boards', data=data)
        if response.status_code != 200:
            logger.error('Deck: Board creation failed!', extra={'response': response})
            raise DeckConnectionException()
        try:
            response_json = response.json()
            board_id = response_json.get('id')
        except Exception:
            logger.error('Deck: Invalid response received!', extra={'response': response})
            raise DeckConnectionException()
        if not board_id:
            logger.error('Deck: No board id returned!', extra={'response': response})
            raise DeckConnectionException()
        data = {
            'type': 1,
            'participant': group.nextcloud_group_id,
            'permissionEdit': True,
            'permissionShare': True,
            'permissionManage': False,
        }
        response = self._api_post(f'/boards/{board_id}/acl', data=data)
        if response.status_code != 200:
            logger.error(
                'Deck: Adding group permissions to board failed!', extra={'response': response, 'board_id': board_id}
            )
            raise DeckConnectionException()
        group.nextcloud_deck_board_id = board_id
        type(group).objects.filter(pk=group.pk).update(nextcloud_deck_board_id=group.nextcloud_deck_board_id)

    def group_board_update(self, group):
        """Updates the group board name and archived status."""
        if not group.nextcloud_deck_board_id:
            # The group deck board id must be set.
            return
        is_board_active = False if not self._is_deck_app_active_for_group(group) else group.is_active
        data = {
            'id': group.nextcloud_deck_board_id,
            'title': group.name,
            'archived': not is_board_active,
            'color': 'ffffff',
        }
        response = self._api_put(f'/boards/{group.nextcloud_deck_board_id}', data=data)
        if response.status_code != 200:
            logger.error(
                'Deck: Board update failed!', extra={'response': response, 'board_id': group.nextcloud_deck_board_id}
            )
            raise DeckConnectionException()

    def group_board_delete(self, group_board_id):
        """Deletes the group board."""
        response = self._api_delete(f'/boards/{group_board_id}')
        if response.status_code != 200:
            # TODO: handle already deleted
            logger.error('Deck: Board deletion failed!', extra={'response': response, 'board_id': group_board_id})
            raise DeckConnectionException()
