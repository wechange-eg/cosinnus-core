from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer

CHANNEL_GROUP_ALL = 'session_all'
CHANNEL_GROUP_ROOM = 'session_%s'


class ClientError(Exception):
    """
    Custom exception class that is caught by the websocket receive()
    handler and translated into a send back to the client.
    """

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class ChatHandlerMixin:
    channel_layer = None
    channel_name = None
    groups = [
        CHANNEL_GROUP_ALL,
    ]

    def receive_json(self, content: dict, **kwargs):
        """
        Calls message receive method based upon command given
        :param content:
        :param kwargs:
        :return:
        """
        command = content.get('command')
        if not command:
            raise ValueError('No command passed in message')
        handler = getattr(self, command, None)
        if handler:
            return handler(self.get_uid(), content)
        else:
            raise ValueError('No handler for message command %s' % content['command'])

    def get_uid(self) -> str:
        """
        Get alphanumeric part from channel name (group names only allow alphanum/hyphens/periods)
        :return:
        """
        return self.channel_name.replace('!', '')


class Consumer(ChatHandlerMixin, JsonWebsocketConsumer):
    """
    Websocket methods called by receive_json
    """

    def sample_command(self, uid: str, data: dict):
        """
        Sample command
        :param uid:
        :param data:
        :return:
        """
        pass


def emit_socket_message(command: str, message: dict, channel_group: str = ''):
    """
    Sends message to all connected websockets within channel group
    :param command:
    :param message:
    :param room:
    :return:
    """
    message['type'] = 'send_json'
    message['command'] = command
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(channel_group or CHANNEL_GROUP_ALL, message)
