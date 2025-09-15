import logging

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from requests.exceptions import JSONDecodeError
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.models.group import get_cosinnus_group_model
from cosinnus.models.tagged import LikeObject, SyncedExternalObject
from cosinnus.utils.permissions import IsNextCloudApiTokenValid, check_ug_admin, check_ug_membership
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.common import apply_follow_object
from cosinnus_cloud.hooks import get_user_by_nc_user_id
from cosinnus_deck import cosinnus_notifications
from cosinnus_deck.api import serializers as deck_serializers
from cosinnus_deck.deck import DeckConnection

logger = logging.getLogger('cosinnus')


class DeckProxyApiMixin:
    """Mixin for Deck Proxy API calls."""

    def check_group_permissions(self, board_id, user):
        """Checks is a group with the board id exists and the user has admin permissions in the board group."""
        group = get_cosinnus_group_model().objects.filter(nextcloud_deck_board_id=board_id).first()
        if not group:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not check_ug_admin(user, group):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        return None

    def proxy_api_call(self, request, api_func, *args, **kwargs):
        """
        Wrapper for DeckConnection API calls.
        Creates a DRF Response using the status code and json content from the API.
        """

        # proxy the x-nc-deck-session header
        extra_header = {}
        x_nc_deck_session_header_value = request.META.get('HTTP_X_NC_DECK_SESSION')
        if x_nc_deck_session_header_value:
            extra_header['x-nc-deck-session'] = x_nc_deck_session_header_value

        response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        try:
            deck = DeckConnection(extra_header=extra_header)
            response = getattr(deck, api_func)(*args, **kwargs)
            response_status = response.status_code
            response_json = response.json()
        except JSONDecodeError:
            response_json = {}
        except Exception:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(status=response_status, data=response_json)


class DeckStacksView(DeckProxyApiMixin, APIView):
    """
    Proxy API to create Deck Stacks.
    See: https://deck.readthedocs.io/en/latest/API/#stacks
    """

    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        request_body=deck_serializers.DeckStackSerializer,
        responses={
            '200': openapi.Response(
                description='Proxy response from the Deck API.',
            )
        },
    )
    def post(self, request, board_id):
        error_response = self.check_group_permissions(board_id, request.user)
        if error_response:
            return error_response

        # validate data
        serializer = deck_serializers.DeckStackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # return proxy api response
        response = self.proxy_api_call(
            request,
            'stack_create',
            board_id,
            serializer.validated_data['title'],
            serializer.validated_data['order'],
            raise_deck_connection_exception=False,
        )
        return response


class DeckStackView(DeckProxyApiMixin, APIView):
    """
    Proxy API to update or delete a Deck Stack.
    See: https://deck.readthedocs.io/en/latest/API/#stacks
    """

    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        request_body=deck_serializers.DeckStackSerializer,
        responses={
            '200': openapi.Response(
                description='Proxy response from the Deck API.',
            )
        },
    )
    def post(self, request, board_id, stack_id):
        error_response = self.check_group_permissions(board_id, request.user)
        if error_response:
            return error_response

        # validate data
        serializer = deck_serializers.DeckStackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # return proxy api response
        response = self.proxy_api_call(
            request,
            'stack_update',
            board_id,
            stack_id,
            serializer.validated_data['title'],
            serializer.validated_data['order'],
            raise_deck_connection_exception=False,
        )
        return response

    def put(self, request, board_id, stack_id):
        return self.post(request, board_id, stack_id)

    def delete(self, request, board_id, stack_id):
        error_response = self.check_group_permissions(board_id, request.user)
        if error_response:
            return error_response

        # return proxy api response
        response = self.proxy_api_call(
            request,
            'stack_delete',
            board_id,
            stack_id,
            raise_deck_connection_exception=False,
        )
        return response


class DeckLabelsView(DeckProxyApiMixin, APIView):
    """
    Proxy API to create Deck labels.
    See: https://deck.readthedocs.io/en/latest/API/#labels
    """

    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        request_body=deck_serializers.DeckLabelSerializer,
        responses={
            '200': openapi.Response(
                description='Proxy response from the Deck API.',
            )
        },
    )
    def post(self, request, board_id):
        error_response = self.check_group_permissions(board_id, request.user)
        if error_response:
            return error_response

        # validate data
        serializer = deck_serializers.DeckLabelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # return proxy api response
        response = self.proxy_api_call(
            request,
            'label_create',
            board_id,
            serializer.validated_data['title'],
            serializer.validated_data['color'],
            raise_deck_connection_exception=False,
        )
        return response


class DeckLabelView(DeckProxyApiMixin, APIView):
    """
    Proxy API to update or delete a Deck label.
    See: https://deck.readthedocs.io/en/latest/API/#labels
    """

    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        request_body=deck_serializers.DeckLabelSerializer,
        responses={
            '200': openapi.Response(
                description='Proxy response from the Deck API.',
            )
        },
    )
    def post(self, request, board_id, label_id):
        error_response = self.check_group_permissions(board_id, request.user)
        if error_response:
            return error_response

        # validate data
        serializer = deck_serializers.DeckLabelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # return proxy api response
        response = self.proxy_api_call(
            request,
            'label_update',
            board_id,
            label_id,
            serializer.validated_data['title'],
            serializer.validated_data['color'],
            raise_deck_connection_exception=False,
        )
        return response

    def put(self, request, board_id, label_id):
        return self.post(request, board_id, label_id)

    def delete(self, request, board_id, label_id):
        error_response = self.check_group_permissions(board_id, request.user)
        if error_response:
            return error_response

        # return proxy api response
        response = self.proxy_api_call(
            request,
            'label_delete',
            board_id,
            label_id,
            raise_deck_connection_exception=False,
        )
        return response


class DeckSyncedTaskMixin:
    """Mixin for synced deck tasks."""

    TYPE_DECK_CARD = 'deck_card'

    def get_deck_group_and_check_permissions(self, user, board_id):
        """Get the group for a board-id and check if user is group member."""
        # get group
        group = get_cosinnus_group_model().objects.filter(nextcloud_deck_board_id=board_id).first()
        if not group:
            raise serializers.ValidationError('Group does not exist.')

        # check group permissions
        if not check_ug_membership(user, group):
            raise serializers.ValidationError('User is not in group.')

        return group

    def get_synced_task(self, user, group, task_id, title=None):
        """Get or create a synced task."""
        synced_task, created = SyncedExternalObject.objects.get_or_create(
            group=group, object_type=self.TYPE_DECK_CARD, object_id=task_id
        )
        if created:
            # set initial synced task parameters
            synced_task.title = title
            synced_task.creator = user
            synced_task.url = group_aware_reverse('cosinnus:deck:index', kwargs={'group': group}) + f'#{task_id}'
            synced_task.icon = 'fa-sticky-note'
            synced_task.save()
        elif synced_task.title != title:
            # task title has changed
            synced_task.title = title
            synced_task.save()
        return synced_task


class DeckEventsView(DeckSyncedTaskMixin, APIView):
    """Handle deck app events. Triggers notifications and auto-follows."""

    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
    )
    permission_classes = (IsNextCloudApiTokenValid,)

    @swagger_auto_schema(
        request_body=deck_serializers.DeckEventSerializer,
        responses={
            '200': openapi.Response(
                description='Event processing succeeded.',
            )
        },
    )
    def post(self, request):
        # serialize base event to get the event type
        serializer = deck_serializers.DeckEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # serialize event
        event_type = serializer.validated_data['type']
        serializer = deck_serializers.get_deck_event_serializer(event_type, data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.validated_data

        # get the user
        nc_user_id = event['requestUserId']
        user = get_user_by_nc_user_id(nc_user_id)
        if not user:
            raise serializers.ValidationError('User does not exist.')

        # get group for deck
        board_id = event['data']['boardId']
        group = self.get_deck_group_and_check_permissions(user, board_id)

        # handle deck event notifications and follows
        self._handle_deck_event(user, group, event)

        return Response()

    def _handle_deck_event(self, user, group, event):
        """Processes a deck event creating notifications and auto-follows depending on the event type."""

        # get or create the synced task
        synced_task = self.get_synced_task(user, group, event['data']['taskId'], event['data']['taskTitle'])
        audience = None
        notifications_signal = None

        if event['type'] == deck_serializers.DECK_EVENT_TYPE_TASK_CREATED:
            # task created
            audience = get_user_model().objects.filter(id__in=group.members).exclude(id=user.id)
            notifications_signal = cosinnus_notifications.deck_task_created
            apply_follow_object(synced_task, user, follow=True)

        elif event['type'] == deck_serializers.DECK_EVENT_TYPE_TASK_STATUS_CHANGED:
            # task status changed
            audience = synced_task.get_followed_users().exclude(id=user.id)
            if event['data']['done']:
                notifications_signal = cosinnus_notifications.following_deck_task_marked_done
            else:
                notifications_signal = cosinnus_notifications.following_deck_task_marked_undone

        elif event['type'] == deck_serializers.DECK_EVENT_TYPE_TASK_DUE_DATE_CHANGED:
            # task due data changed
            audience = synced_task.get_followed_users().exclude(id=user.id)
            notifications_signal = cosinnus_notifications.following_deck_task_due_date_changed

        elif event['type'] == deck_serializers.DECK_EVENT_TYPE_TASK_ASSIGNEE_CHANGED:
            # task assignee changed
            assignee = get_user_by_nc_user_id(event['data']['userId'])
            if not assignee:
                raise serializers.ValidationError('Assignee does not exist.')
            if assignee != user:
                audience = [assignee]
                if event['data']['assigned']:
                    # user got assigned
                    notifications_signal = cosinnus_notifications.deck_task_user_assigned
                    apply_follow_object(synced_task, assignee, follow=True)
                else:
                    # user got unassigned
                    notifications_signal = cosinnus_notifications.deck_task_user_unassigned

        elif event['type'] == deck_serializers.DECK_EVENT_TYPE_TASK_COMMENT_CREATED:
            # task comment posted
            audience = synced_task.get_followed_users().exclude(id=user.id)
            notifications_signal = cosinnus_notifications.following_deck_task_comment_posted
            apply_follow_object(synced_task, user, follow=True)

        elif event['type'] == deck_serializers.DECK_EVENT_TYPE_TASK_USER_MENTIONED:
            # user mentioned in task comment
            mentioned_user = get_user_by_nc_user_id(event['data']['userId'])
            if not mentioned_user:
                raise serializers.ValidationError('User does not exist.')
            if mentioned_user != user:
                audience = [mentioned_user]
                notifications_signal = cosinnus_notifications.deck_task_user_mentioned
                apply_follow_object(synced_task, mentioned_user, follow=True)

        elif event['type'] == deck_serializers.DECK_EVENT_TYPE_TASK_DELETED:
            # task deleted
            synced_task.delete()

        # send notification signal if set.
        if notifications_signal and audience and synced_task:
            notifications_signal.send(
                sender=synced_task,
                user=user,
                obj=synced_task,
                audience=audience,
            )


class DeckFollowView(DeckSyncedTaskMixin, APIView):
    """Follow/unfollow deck tasks."""

    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        request_body=deck_serializers.DeckFollowSerializer,
        responses={
            '200': openapi.Response(
                description='Follow/unfollow processing succeeded.',
            )
        },
    )
    def post(self, request, board_id):
        # serialize request
        serializer = deck_serializers.DeckFollowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # get group
        group = self.get_deck_group_and_check_permissions(request.user, board_id)

        # get synced task
        synced_task = self.get_synced_task(request.user, group, serializer.validated_data['id'])

        # follow / unfollow task
        apply_follow_object(synced_task, request.user, follow=serializer.validated_data['follow'])

        return Response()

    def get(self, request, board_id):
        # get group
        group = self.get_deck_group_and_check_permissions(request.user, board_id)

        # get user follows for synced external objects
        content_type = ContentType.objects.get_for_model(SyncedExternalObject)
        follows = LikeObject.objects.filter(user=request.user, followed=True, content_type=content_type)

        # filter follows for deck-cards and group
        card_follows = [
            follow
            for follow in follows
            if follow.target_object.object_type == self.TYPE_DECK_CARD and follow.target_object.group == group
        ]

        # return follows
        data = [{'type': 'card', 'id': int(card_follow.target_object.object_id)} for card_follow in card_follows]
        return Response(data=data)
