# -*- coding: utf-8 -*-
import random

from captcha.conf import settings
from six import u


def dissimilar_random_char_challenge():
    """A django-simple-captcha generator function that uses
    only chars that can not easily be confused in the captcha,
    like confusion between 'O' and 'Q'.
    Removed: R, P, Q, O, K, X, I, J, V, Z, F, S, D
    """

    chars, ret = u('abcfghlmntuwy'), u('')
    for i in range(settings.CAPTCHA_LENGTH):
        ret += random.choice(chars)
    return ret.upper(), ret
