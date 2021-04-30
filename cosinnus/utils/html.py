# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from cosinnus.utils.urls import BETTER_URL_RE
from cosinnus.models.group import CosinnusPortal
from django.utils.safestring import mark_safe


def replace_non_portal_urls(html_text, replacement_url=None, portal_url=None):
    """ Replaces all URLs in html text that do not point to `portal_url` as domain,
        with a replacement URL. """
    
    if portal_url is None:
        portal_url = CosinnusPortal.get_current().get_domain()
    if replacement_url is None:
        replacement_url = portal_url
    # add a GET param to show a redirect warning to the user 
    # (handled by `ExternalEmailLinkRedirectNoticeMiddleware`)
    append_param_arg = '?' if not '?' in replacement_url else '&'
    replacement_url = f'{replacement_url}{append_param_arg}external_link_redirect=1'
    
    for m in reversed([it for it in BETTER_URL_RE.finditer(html_text)]):
        matched_url = m.group()
        if not matched_url.startswith(portal_url):
            html_text = html_text[:m.start()] + replacement_url + html_text[m.end():]
    return html_text


def render_html_with_variables(user, html, variables=None):
    """ Renders any raw HTML with some request context variables """
    from cosinnus.templatetags.cosinnus_tags import full_name
    if variables is None:
            variables = {}
    variables.update({
        'user_first_name': user.first_name,
        'user_last_name': user.last_name,
        'user_full_name': full_name(user),
    })
    for variable_name, variable_value in variables.items():
        html = html.replace('[[%s]]' % variable_name, str(variable_value))
    return mark_safe(html)

