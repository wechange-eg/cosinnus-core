import datetime
import logging
from datetime import timezone

import requests
from django.utils import timezone as django_timezone

from cosinnus.conf import settings
from cosinnus.models.tagged import BaseTagObject
from cosinnus_cloud.hooks import get_nc_user_id, initialize_nextcloud_for_group
from cosinnus_cloud.utils.nextcloud import add_user_to_group
from cosinnus_todo.models import TodoList

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
        if board_details and settings.COSINNUS_DECK_GROUP_BOARD_DELETE_DEFAULT_LABELS:
            default_labels = board_details.get('labels')
            if default_labels:
                for label in default_labels:
                    label_title = label.get('title')
                    label_id = label.get('id')
                    if (
                        label_id
                        and label_title
                        and label_title in settings.COSINNUS_DECK_GROUP_BOARD_DELETE_DEFAULT_LABELS
                    ):
                        self.label_delete(board_id, label_id, raise_deck_connection_exception=False)

        # create initial stacks
        initial_content = settings.COSINNUS_DECK_GROUP_BOARD_INITIAL_CONTENT
        if initial_content:
            # create labels
            for label_title, label_color in initial_content.get('labels'):
                self.label_create(board_id, label_title, label_color, raise_deck_connection_exception=False)

            # create stacks
            portal_url = group.portal.get_domain()
            stack_order = 0
            for stack in initial_content.get('stacks'):
                response = self.stack_create(
                    board_id, stack['title'], stack_order, raise_deck_connection_exception=False
                )
                if response.status_code != 200:
                    continue
                try:
                    stack_id = response.json().get('id')
                except Exception:
                    logger.warning('Deck: Invalid response received!', extra={'response': response})
                    continue
                stack_order += 1

                # create cards
                card_order = 0
                for card in stack.get('cards', []):
                    # render description with portal_url
                    description = card['description'] % {'portal_url': portal_url}
                    self.card_create(
                        board_id,
                        stack_id,
                        card['title'],
                        card_order,
                        description=description,
                        raise_deck_connection_exception=False,
                    )
                    card_order += 1

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

    def stack_list(self, group_board_id, raise_deck_connection_exception=True):
        """
        Get the board stacks.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        response = self._api_get(f'/boards/{group_board_id}/stacks')
        if response.status_code != 200:
            logger.warning(
                'Deck: Stack list failed!',
                extra={'response': response, 'board_id': group_board_id},
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

    def _get_utc_datetime(self, date):
        """Helper to get a date/datetime instance into the utc format used by nextcloud."""
        if isinstance(date, datetime.date):
            date = datetime.datetime(date.year, date.month, date.day)
        return django_timezone.make_aware(date).astimezone(timezone.utc).isoformat()

    def card_create(
        self,
        group_board_id,
        stack_id,
        title,
        order,
        description=None,
        due_date=None,
        raise_deck_connection_exception=True,
    ):
        """
        Creates a board card.
        @param due_date: Optional date or datetime instance
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        data = {
            'title': title,
            'order': order,
        }
        if description:
            data['description'] = description
        if due_date:
            data['duedate'] = self._get_utc_datetime(due_date)
        response = self._api_post(f'/boards/{group_board_id}/stacks/{stack_id}/cards', data=data)
        if response.status_code != 200:
            logger.warning(
                'Deck: Card creation failed!',
                extra={'response': response, 'board_id': group_board_id, 'stack_id': stack_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def card_assign_user(self, group_board_id, stack_id, card_id, user, raise_deck_connection_exception=True):
        """
        Assign a user to a card.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        data = {
            'userId': get_nc_user_id(user),
        }
        response = self._api_put(f'/boards/{group_board_id}/stacks/{stack_id}/cards/{card_id}/assignUser', data=data)
        if response.status_code != 200:
            logger.warning(
                'Deck: Card user assignment failed!',
                extra={'response': response, 'board_id': group_board_id, 'stack_id': stack_id, 'card_id': card_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def card_set_done(
        self, group_board_id, stack_id, card_id, done_datetime=None, raise_deck_connection_exception=True
    ):
        """
        Sets the done status of a card.
        Returns the response. Pass raise_deck_connection_exception=False to receive error response instead of exception.
        """
        response = self._api_get(f'/boards/{group_board_id}/stacks/{stack_id}/cards/{card_id}')
        if response.status_code != 200:
            logger.warning(
                'Deck: Card setting done failed!',
                extra={'response': response, 'board_id': group_board_id, 'stack_id': stack_id, 'card_id': card_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
            else:
                return response
        try:
            data = response.json()
        except Exception:
            logger.warning('Deck: Invalid response received!', extra={'response': response})
            if raise_deck_connection_exception:
                raise DeckConnectionException()
            else:
                return response
        data['done'] = self._get_utc_datetime(done_datetime) if done_datetime else None
        response = self._api_put(f'/boards/{group_board_id}/stacks/{stack_id}/cards/{card_id}', data=data)
        if response.status_code != 200:
            logger.warning(
                'Deck: Card setting done failed!',
                extra={'response': response, 'board_id': group_board_id, 'stack_id': stack_id, 'card_id': card_id},
            )
            if raise_deck_connection_exception:
                raise DeckConnectionException()
        return response

    def group_migrate_todo(self, group):
        """Migrate todos to deck app."""

        # set migration status
        group.deck_todo_migration_set_status(group.DECK_TODO_MIGRATION_STATUS_IN_PROGRESS)
        try:
            if not group.nextcloud_group_id:
                # initialize nextcloud group
                initialize_nextcloud_for_group(group, send_initialized_signal=False)
                for user in group.actual_members:
                    add_user_to_group(get_nc_user_id(user), group.nextcloud_group_id)

            if not group.nextcloud_deck_board_id:
                # initialize deck
                self.group_board_create(group, initialize_board_content=True)

            # get the next free stack order
            response = self.stack_list(group_board_id=group.nextcloud_deck_board_id)
            stack_order = len(response.json())

            # migrate todos to the deck
            todo_lists = TodoList.objects.filter(group=group)
            for todo_list in todo_lists:
                todo_query = todo_list.todos.exclude(media_tag__visibility=BaseTagObject.VISIBILITY_USER)
                todo_query = todo_query.filter(media_tag__migrated=False)
                if not todo_query.exists():
                    # nothing to migrate
                    continue

                list_title = todo_list.title if not todo_list.is_general_list() else 'General'
                response = self.stack_create(
                    group_board_id=group.nextcloud_deck_board_id,
                    title=list_title,
                    order=stack_order,
                )
                stack_id = response.json()['id']

                stack_order += 1
                card_order = 0

                for todo in todo_query.filter(media_tag__migrated=False):
                    # get description with comments and attached objects
                    description = todo.note
                    if todo.attached_objects.exists():
                        attachments = '\n\nAttachments:\n\n'
                        for attachment in todo.attached_objects.all():
                            if hasattr(attachment.target_object, 'get_absolute_url'):
                                url = attachment.target_object.get_absolute_url()
                                attachments += f'- [{url}]({url})\n'
                        attachments += '\n\n'
                        description += attachments
                    if todo.comments.exists():
                        comments = '\n\nComments:\n\n'
                        for comment in todo.comments.all():
                            creator = comment.creator.get_full_name()
                            comments += f'- {creator}: {comment.text}\n'
                        description += comments

                    response = self.card_create(
                        group_board_id=group.nextcloud_deck_board_id,
                        stack_id=stack_id,
                        title=todo.title,
                        order=card_order,
                        description=description,
                        due_date=todo.due_date,
                    )
                    card_id = response.json()['id']

                    # assign user
                    if todo.assigned_to:
                        self.card_assign_user(
                            group_board_id=group.nextcloud_deck_board_id,
                            stack_id=stack_id,
                            card_id=card_id,
                            user=todo.assigned_to,
                        )

                    # set done
                    if todo.completed_date:
                        self.card_set_done(
                            group_board_id=group.nextcloud_deck_board_id,
                            stack_id=stack_id,
                            card_id=card_id,
                            done_datetime=todo.completed_date,
                        )

                    # mark todos as migrated
                    todo.media_tag.migrated = True
                    todo.media_tag.save()

            # deactivate todos and activate deck, if not active
            deactivate_apps = set(group.get_deactivated_apps())
            deactivate_apps.add('cosinnus_todo')
            if 'cosinnus_deck' in deactivate_apps:
                deactivate_apps.remove('cosinnus_deck')
            group.deactivated_apps = deactivate_apps
            type(group).objects.filter(pk=group.pk).update(deactivated_apps=group.deactivated_apps)

            # set migration status
            group.deck_todo_migration_set_status(group.DECK_TODO_MIGRATION_STATUS_SUCCESS)
        except Exception as e:
            logger.warning(
                'Deck: Todo migration failed!',
                extra={'group': group.id, 'board_id': group.nextcloud_deck_board_id, 'exception': e},
            )
            group.deck_todo_migration_set_status(group.DECK_TODO_MIGRATION_STATUS_FAILED)
