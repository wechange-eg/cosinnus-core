from cosinnus.conf import settings


class RelayMessageMixin:
    """ Utility function mixin for a BaseTaggableObject model relaying messages to Rocket Chat. """

    def get_message_emote(self):
        return settings.COSINNUS_ROCKET_NEWS_BOT_EMOTE

    def get_message_title(self):
        raise NotImplementedError

    def get_message_text(self):
        raise NotImplementedError
