# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from cosinnus.utils.urls import BETTER_URL_RE
from cosinnus.models.group import CosinnusPortal


def replace_non_portal_urls(html_text, replacement_url, portal_url=None):
    """ Replaces all URLs in html text that do not point to `portal_url` as domain,
        with a replacement URL. """
    
    if portal_url is None:
        portal_url = CosinnusPortal.get_current().get_domain()
    
    for m in reversed([it for it in BETTER_URL_RE.finditer(html_text)]):
        matched_url = m.group()
        if not matched_url.startswith(portal_url):
            html_text = html_text[:m.start()] + replacement_url + html_text[m.end():]
    return html_text