import datetime
import logging
from datetime import timezone

import requests
from django.utils import timezone as django_timezone

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusGroup, CosinnusPortal
from cosinnus.models.tagged import BaseTagObject
from cosinnus.templatetags.cosinnus_tags import textfield
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

        # create initial board content
        if initialize_board_content:
            self.group_board_initialize(board_id, board_details=board_details)

        # save board id for the group
        group.refresh_from_db()
        if not group.nextcloud_deck_board_id:
            # no board was created in parallel.
            group.nextcloud_deck_board_id = board_id
            type(group).objects.filter(pk=group.pk).update(nextcloud_deck_board_id=group.nextcloud_deck_board_id)
            group.clear_cache()

    def group_board_initialize(self, group_board_id, board_details=None):
        """
        Initialize group board with content from COSINNUS_DECK_GROUP_BOARD_INITIAL_CONTENT.
        @param board_details: Response data from the board create/get call containing board details.
        """
        # get board details if not provided
        if not board_details:
            response = self._api_get(f'/boards/{group_board_id}')
            if response.status_code != 200:
                logger.warning(
                    'Deck: Getting board details failed!', extra={'response': response, 'board_id': group_board_id}
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
                        self.label_delete(group_board_id, label_id, raise_deck_connection_exception=False)

        # create initial stacks
        initial_content = settings.COSINNUS_DECK_GROUP_BOARD_INITIAL_CONTENT
        if initial_content:
            # create labels
            for label_title, label_color in initial_content.get('labels'):
                self.label_create(group_board_id, label_title, label_color, raise_deck_connection_exception=False)

            # create stacks
            portal_url = CosinnusPortal.get_current().get_domain()
            stack_order = 0
            for stack in initial_content.get('stacks'):
                response = self.stack_create(
                    group_board_id, stack['title'], stack_order, raise_deck_connection_exception=False
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
                        group_board_id,
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
        Note: Used in the DeckStackView proxy API view.
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
        Note: Used in the DeckStackView proxy API view.
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
        Note: Used in the DeckStackView proxy API view.
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
        Note: Used in the DeckStackView proxy API view.
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
        Note: Used in the DeckStackView proxy API view.
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
        group.deck_migration_set_status(group.DECK_MIGRATION_STATUS_IN_PROGRESS)
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

                for todo in todo_query:
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
                            comments += f'- {creator}:\n{comment.text}\n'
                        description += comments

                    # convert to html
                    description = textfield(description)

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
            group.deck_migration_set_status(group.DECK_MIGRATION_STATUS_SUCCESS)

            # clear group cache
            group._clear_cache(group=group)
        except Exception as e:
            logger.warning(
                'Deck: Todo migration failed!',
                extra={'group': group.id, 'board_id': group.nextcloud_deck_board_id, 'exception': e},
            )
            group.deck_migration_set_status(group.DECK_MIGRATION_STATUS_FAILED)

    def migrate_user_decks(self, user, selected_decks):
        """
        Migrate user decks to group decks.
        @param selected_decks: List of dicts containing board- and group-ids, e.g. [{"board": 1, "group": 2 }, ...].
        """

        # set migration status
        user.cosinnus_profile.deck_migration_set_status(user.cosinnus_profile.DECK_MIGRATION_STATUS_IN_PROGRESS)
        try:
            for selected_deck in selected_decks:
                board_id = selected_deck['board']
                group_id = selected_deck['group']

                # get group
                group = CosinnusGroup.objects.get(pk=group_id)

                if not group.nextcloud_group_id:
                    # initialize nextcloud group
                    initialize_nextcloud_for_group(group, send_initialized_signal=False)
                    for user in group.actual_members:
                        add_user_to_group(get_nc_user_id(user), group.nextcloud_group_id)

                if not group.nextcloud_deck_board_id:
                    # initialize deck
                    self.group_board_create(group, initialize_board_content=True)
                group_board_id = group.nextcloud_deck_board_id

                # get group board data
                response = self._api_get(f'/boards/{group_board_id}')
                if response.status_code != 200:
                    raise DeckConnectionException('Get group board failed.')
                group_board_data = response.json()

                # get existing labels as duplicates are not allowed by the api
                existing_labels = {label['title']: label['id'] for label in group_board_data.get('labels', [])}

                # get last stack number to add new stacks after it
                if group_board_data['stacks']:
                    stack_order = max(stack['order'] for stack in group_board_data['stacks']) + 1
                else:
                    stack_order = 1

                # get user board
                response = self._api_get(f'/boards/{board_id}')
                if response.status_code != 200:
                    raise DeckConnectionException('Failed to get user board.')
                board_data = response.json()

                # add users to group board to be able to assign them to cards before they join the group.
                group_board_users = [settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME, group.nextcloud_group_id]
                for acl_data in group_board_data['acl']:
                    if acl_data['participant']['uid'] in group_board_users:
                        # ignore existing default participants
                        continue
                    migrated_acl_data = {
                        'type': acl_data['type'],
                        'participant': acl_data['particpant'],
                        'permissionEdit': False,
                        'permissionShare': False,
                        'permissionManage': False,
                    }
                    response = self._api_post(f'/boards/{group_board_id}/acl', data=migrated_acl_data)
                    if response.status_code != 200:
                        raise DeckConnectionException('Acl migration failed.')

                # migrate labels, save label ids in dict to be used in assignment
                labels = existing_labels.copy()
                for label_data in board_data['labels']:
                    if label_data['title'] in existing_labels.keys():
                        continue
                    migrated_label_data = {'title': label_data['title'], 'color': label_data['color']}
                    response = self._api_post(f'/boards/{group_board_id}/labels', data=migrated_label_data)
                    if response.status_code != 200:
                        raise DeckConnectionException('Label migration failed.')
                    migrated_label_data = response.json()
                    labels[migrated_label_data['title']] = migrated_label_data['id']

                # migrate stacks and cards
                response = self.stack_list(group_board_id=board_id)
                if response.status_code != 200:
                    raise DeckConnectionException('Failed to get stacks.')
                stacks_data = response.json()
                for stack_data in stacks_data:
                    # migrate stack
                    migrated_stack_data = {'title': stack_data['title'], 'order': stack_order}
                    stack_order += 1
                    response = self._api_post(f'/boards/{group_board_id}/stacks', data=migrated_stack_data)
                    if response.status_code != 200:
                        raise DeckConnectionException('Stack migration failed.')
                    migrated_stack_data = response.json()
                    migrated_stack_id = migrated_stack_data['id']

                    for card_data in stack_data.get('cards', []):
                        card_id = card_data['id']

                        # Get attachments (attachment API did not return any files, falling back to the FE url).
                        # There is no way to migrate attachments, so we just add links to the files to the description.
                        attachment_list = ''
                        attachment_url = (
                            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/apps/deck/cards/{card_id}/attachments'
                        )
                        response = requests.get(attachment_url, **self._api_params)
                        if response.status_code != 200:
                            raise DeckConnectionException('Get attachments failed.')
                        attachments_data = response.json()
                        if attachments_data:
                            attachment_list = '\n\nAttachments:\n\n'
                            for attachment_data in attachments_data:
                                fileid = attachment_data.get('extendedData', {}).get('fileid')
                                filename = attachment_data.get('data')
                                if fileid and filename:
                                    attachment_list += (
                                        f'- [{filename}]({settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/f/{fileid})'
                                    )

                        # append attachments to description
                        description = card_data.get('description', '')
                        if attachment_list:
                            description += attachment_list

                        # convert description to html
                        if description:
                            description = textfield(description)

                        migrated_card_data = {
                            'title': card_data['title'],
                            'order': card_data['order'],
                            'description': description,
                            'duedate': card_data['duedate'],
                        }
                        response = self._api_post(
                            f'/boards/{group_board_id}/stacks/{migrated_stack_id}/cards', data=migrated_card_data
                        )
                        if response.status_code != 200:
                            raise DeckConnectionException('Label migration failed.')
                        migrated_card_data = response.json()
                        migrated_card_id = migrated_card_data['id']

                        # set done (does not work in the initial create post)
                        if card_data['done']:
                            migrated_card_data['done'] = card_data['done']
                            response = self._api_put(
                                f'/boards/{group_board_id}/stacks/{migrated_stack_id}/cards/{migrated_card_id}',
                                data=migrated_card_data,
                            )
                            if response.status_code != 200:
                                raise DeckConnectionException('Setting card as done failed.')

                        # assign users
                        for assigned_user_data in card_data['assignedUsers']:
                            migrate_assigned_user_data = {'userId': assigned_user_data['participant']['uid']}
                            response = self._api_put(
                                f'/boards/{group_board_id}/stacks/{migrated_stack_id}/cards/{migrated_card_id}/assignUser',
                                data=migrate_assigned_user_data,
                            )
                            if response.status_code != 200:
                                raise DeckConnectionException('Assigned user migration failed.')

                        # migrate card label
                        for label_data in card_data.get('labels', []):
                            migrated_label_data = {'labelId': labels[label_data['title']]}
                            response = self._api_put(
                                f'/boards/{group_board_id}/stacks/{migrated_stack_id}/cards/{migrated_card_id}/assignLabel',
                                data=migrated_label_data,
                            )
                            if response.status_code != 200:
                                raise DeckConnectionException('Card label migration failed.')

                        # migrate comments (not part of the deck api)
                        comments_url = (
                            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}'
                            f'/ocs/v2.php/apps/deck/api/v1.0/cards/{card_id}/comments'
                        )
                        migrated_comments_url = (
                            f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}'
                            f'/ocs/v2.php/apps/deck/api/v1.0/cards/{migrated_card_id}/comments'
                        )
                        response = requests.get(comments_url, **self._api_params)
                        if response.status_code != 200:
                            raise DeckConnectionException('Get card comments failed.')
                        comments_data = response.json()
                        for comment_data in reversed(comments_data['ocs']['data']):
                            comment_user = comment_data['actorDisplayName']
                            comment_message = comment_data['message']
                            migrated_comment_data = {'message': f'{comment_user}: {comment_message}'}
                            response = requests.post(
                                migrated_comments_url, json=migrated_comment_data, **self._api_params
                            )
                            if response.status_code != 200:
                                raise DeckConnectionException('Migrating card comments failed.')

            # set migration status
            user.cosinnus_profile.deck_migration_set_status(user.cosinnus_profile.DECK_MIGRATION_STATUS_SUCCESS)
        except Exception as e:
            logger.warning(
                'Deck: User deck migration failed!',
                extra={'user': user.id, 'selected_decks': selected_decks, 'exception': e},
            )
            user.cosinnus_profile.deck_migration_set_status(user.cosinnus_profile.DECK_MIGRATION_STATUS_FAILED)
