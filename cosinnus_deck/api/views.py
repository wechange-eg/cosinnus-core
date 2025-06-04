import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from requests.exceptions import JSONDecodeError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.models.group import (
    get_cosinnus_group_model,
)
from cosinnus.utils.permissions import check_ug_admin
from cosinnus_deck.api.serializers import DeckLabelSerializer, DeckStackSerializer
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
        request_body=DeckStackSerializer,
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
        serializer = DeckStackSerializer(data=request.data)
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
        request_body=DeckStackSerializer,
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
        serializer = DeckStackSerializer(data=request.data)
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
        request_body=DeckLabelSerializer,
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
        serializer = DeckLabelSerializer(data=request.data)
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
        request_body=DeckLabelSerializer,
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
        serializer = DeckLabelSerializer(data=request.data)
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
