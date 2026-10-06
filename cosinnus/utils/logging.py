# -*- coding: utf-8 -*-
import logging

import sentry_sdk

logger = logging.getLogger('cosinnus')


def log_needs_attention_error(message, extra=None):
    """Logs a critical error with the wechange:needs_attention tag that can be filtered for in glitch/sentry.
    Useful for logging situations that require fast attention for configuration changes or severe outages."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag('wechange', 'needs_attention')
        logger.critical(message, extra=extra)


def log_with_tags(level, message, tags=dict, extra=None):
    """Logs any a message with variable level with a given set of tags.
    Level is a const taken directly from the logging package: `logging.WARNING` or `logging.CRITICAL`
    Tags need to be in the form of `{'tag_name': 'tag_value', ...}`."""
    with sentry_sdk.configure_scope() as scope:
        if tags:
            for key, val in tags.items():
                scope.set_tag(key, val)
        logger.log(level, message, extra=extra)
