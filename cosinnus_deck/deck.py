import logging

import requests

from cosinnus.conf import settings

logger = logging.getLogger(__name__)


class DeckConnectionException(Exception):
    """Exception raised when a dock api call failed."""

    pass


class DeckConnection:
    BASE_URL = f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/index.php/apps/deck/api/v1.0'

    # API parameter including auth and header set in __init__
    _api_params = None

    def __init__(self, extra_header=None):
        headers = {'OCS-APIRequest': 'true', 'Accept': 'application/json'}
        if extra_header:
            headers.update(**extra_header)
        self._api_params = {'auth': settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH, 'headers': headers}

    def _api_get(self, url):
        """API GET wrapper."""
        return requests.get(self.BASE_URL + url, **self._api_params)

    def _api_post(self, url, data):
        """API POST wrapper."""
        return requests.post(self.BASE_URL + url, json=data, **self._api_params)

    def _api_put(self, url, data):
        """API PUT wrapper."""
        return requests.put(self.BASE_URL + url, json=data, **self._api_params)

    def _api_delete(self, url):
        """API DELETE wrapper."""
        return requests.delete(self.BASE_URL + url, **self._api_params)

    def _is_deck_app_active_for_group(self, group):
        """Check if the deck app activated in a group."""
        return 'cosinnus_deck' not in group.get_deactivated_apps()

    def group_board_create(self, group, initialize_board_content=True):
        """Creates a Deck board for a group and adds the group permissions to it."""
        if not group.nextcloud_group_id:
            # Nextcloud group id is required to create a group board.
            return
        if group.nextcloud_deck_board_id:
            # Group already has a deck board created.
            return

        # create the board
        board_details = None
        data = {'title': group.name, 'color': 'ffffff'}
        response = self._api_post('/boards', data=data)
        if response.status_code != 200:
            logger.warning('Deck: Board creation failed!', extra={'response': response})
            raise DeckConnectionException()
        try:
            board_details = response.json()
            board_id = board_details.get('id')
        except Exception:
            logger.warning('Deck: Invalid response received!', extra={'response': response})
            raise DeckConnectionException()
        if not board_id:
            logger.warning('Deck: No board id returned!', extra={'response': response})
            raise DeckConnectionException()

        # give group permissions to the new board
        data = {
            'type': 1,
            'participant': group.nextcloud_group_id,
            'permissionEdit': True,
            'permissionShare': False,
            'permissionManage': False,
        }
        response = self._api_post(f'/boards/{board_id}/acl', data=data)
        if response.status_code != 200:
            logger.warning(
                'Deck: Adding group permissions to board failed!', extra={'response': response, 'board_id': board_id}
            )
            raise DeckConnectionException()

        # save board id for the group
        group.refresh_from_db()
        if not group.nextcloud_deck_board_id:
            # no board was created in parallel.
            group.nextcloud_deck_board_id = board_id
            type(group).objects.filter(pk=group.pk).update(nextcloud_deck_board_id=group.nextcloud_deck_board_id)
            group.clear_cache()

        # create initial board content
        if initialize_board_content:
            self.group_board_initialize(group, board_details=board_details)

    def group_board_initialize(self, group, board_details=None):
        """
        Initialize group board with content from COSINNUS_DECK_GROUP_BOARD_INITIAL_CONTENT.
        @param board_details: Response data from the board create/get call containing board details.
        """
        if not group.nextcloud_deck_board_id:
            # The group deck board id must be set.
            return
        board_id = group.nextcloud_deck_board_id

        # get board details if not provided
        if not board_details:
            response = self._api_get(f'/boards/{board_id}')
            if response.status_code != 200:
                logger.warning(
                    'Deck: Getting board details failed!', extra={'response': response, 'board_id': board_id}
                )
            try:
                board_details = response.json()
            except Exception:
                logger.warning('Deck: Invalid response received!', extra={'response': response})

        # delete default labels
        if board_details:
            default_labels = board_details.get('labels')
            if default_labels:
                for label in default_labels:
                    label_id = label.get('id')
                    if label_id:
                        self.label_delete(board_id, label_id, raise_deck_connection_exception=False)

        # create initial stacks
        initial_content = settings.COSINNUS_DECK_GROUP_BOARD_INITIAL_CONTENT
        if initial_content:
            # create labels
            for label_title, label_color in initial_content.get('labels'):
                self.label_create(board_id, label_title, label_color, raise_deck_connection_exception=False)

            # create stacks
            portal_url = group.portal.get_domain()
            for stack in initial_content.get('stacks'):
                response = self.stack_create(
                    board_id, stack['title'], stack['order'], raise_deck_connection_exception=False
                )
                if response.status_code != 200:
                    continue
                try:
                    stack_id = response.json().get('id')
                except Exception:
                    logger.warning('Deck: Invalid response received!', extra={'response': response})
                    continue

                # create cards
                for card in stack.get('cards', []):
                    # render description with portal_url
                    description = card['description'] % {'portal_url': portal_url}
                    self.card_create(
                        board_id,
                        stack_id,
                        card['title'],
                        card['order'],
                        description=description,
                        raise_deck_connection_exception=False,
                    )

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
            logger.warning(
                'Deck: Board update failed!', extra={'response': response, 'board_id': group.nextcloud_deck_board_id}
            )
            raise DeckConnectionException()

    def group_board_delete(self, group_board_id):
        """Deletes the group board."""
        response = self._api_delete(f'/boards/{group_board_id}')
        if response.status_code != 200:
            logger.warning('Deck: Board deletion failed!', extra={'response': response, 'board_id': group_board_id})
            raise DeckConnectionException()

    def stack_create(self, group_board_id, title, order, raise_deck_connection_exception=True):
        """
        Creates a board stack.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        data = {
            'title': title,
            'order': order,
        }
        response = self._api_post(f'/boards/{group_board_id}/stacks', data=data)
        if response.status_code != 200:
            logger.warning('Deck: Stack creation failed!', extra={'response': response, 'board_id': group_board_id})
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def stack_update(self, group_board_id, stack_id, title, order, raise_deck_connection_exception=True):
        """
        Updates a board stack.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        data = {
            'title': title,
            'order': order,
        }
        response = self._api_put(f'/boards/{group_board_id}/stacks/{stack_id}', data=data)
        if response.status_code != 200:
            logger.warning(
                'Deck: Stack update failed!',
                extra={'response': response, 'board_id': group_board_id, 'stack_id': stack_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def stack_delete(self, group_board_id, stack_id, raise_deck_connection_exception=True):
        """
        Deletes a board stack.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        response = self._api_delete(f'/boards/{group_board_id}/stacks/{stack_id}')
        if response.status_code != 200:
            logger.warning(
                'Deck: Stack delete failed!',
                extra={'response': response, 'board_id': group_board_id, 'stack_id': stack_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def label_create(self, group_board_id, title, color, raise_deck_connection_exception=True):
        """
        Creates a board label.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        data = {
            'title': title,
            'color': color,
        }
        response = self._api_post(f'/boards/{group_board_id}/labels', data=data)
        if response.status_code != 200:
            logger.warning('Deck: Label creation failed!', extra={'response': response, 'board_id': group_board_id})
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def label_update(self, group_board_id, label_id, title, color, raise_deck_connection_exception=True):
        """
        Updates a board label.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        data = {
            'title': title,
            'color': color,
        }
        response = self._api_put(f'/boards/{group_board_id}/labels/{label_id}', data=data)
        if response.status_code != 200:
            logger.warning(
                'Deck: Label update failed!',
                extra={'response': response, 'board_id': group_board_id, 'label_id': label_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def label_delete(self, group_board_id, label_id, raise_deck_connection_exception=True):
        """
        Deletes a board label.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        response = self._api_delete(f'/boards/{group_board_id}/labels/{label_id}')
        if response.status_code != 200:
            logger.warning(
                'Deck: Label delete failed!',
                extra={'response': response, 'board_id': group_board_id, 'label_id': label_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def card_create(
        self, group_board_id, stack_id, title, order, description=None, raise_deck_connection_exception=True
    ):
        """
        Creates a board card.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        data = {
            'title': title,
            'order': order,
        }
        if description:
            data['description'] = description
        response = self._api_post(f'/boards/{group_board_id}/stacks/{stack_id}/cards', data=data)
        if response.status_code != 200:
            logger.warning(
                'Deck: Card creation failed!',
                extra={'response': response, 'board_id': group_board_id, 'stack_id': stack_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response
