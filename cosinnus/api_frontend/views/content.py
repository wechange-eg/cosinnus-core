import logging
import re
from copy import copy
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.http import QueryDict, HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from announcements.models import Announcement
from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.core.decorators.views import get_group_for_request
from cosinnus.core.middleware.frontend_middleware import FrontendMiddleware
from cosinnus.models import CosinnusPortal
from cosinnus.models.user_dashboard import MenuItem, FONT_AWESOME_CLASS_FILTER
from cosinnus.utils.functions import uniquify_list
from cosinnus.utils.http import remove_url_param, add_url_param
from cosinnus.conf import settings
from cosinnus.utils.context_processors import email_verified as email_verified_context_processor

logger = logging.getLogger('cosinnus')


# url prefixes that make the requested url be considered to belong in the "community" space
V3_CONTENT_COMMUNITY_URL_PREFIXES = [
    '/map/',
    '/user_match/'
]
# url suffixes for links from the leftnav that should be sorted into the top sidebar list
V3_CONTENT_TOP_SIDEBAR_URL_SUFFIXES = [
    '/microsite/'
]
# url suffixes for links from the leftnav that should be sorted into the bottom sidebar list
V3_CONTENT_BOTTOM_SIDEBAR_URL_SUFFIXES = [
    '/members/',
    '/edit/',
    '/delete/',
    '/password_change/'
]


class MainContentView(APIView):
    """ v3_content_main
    
    An endpoint that returns HTML content for any legacy view on the portal.
    Will not work on URL targets that match exemptions defined in `COSINNUS_V3_FRONTEND_EVERYWHERE_URL_PATTERN_EXEMPTIONS`
    
    Return values:
      * `resolved_url`: the resolved URL of the queried `url` parameter where the content HTML is delivered from, or if `redirect==True`, the target URL to redirect to
      * `redirect": (bool) whether the target URL was resolved and HTML content is returned in this data package, or, if True, the data package is empty and a redirect should be performed to `resolved_url`
      * `status_code`: (int), HTTP status code of the response for the request sent to the `resolved_url`
      * `content_html`: html from the `<div class="container">` frame to be inserted
      * `footer_html`: html from the footer, to be inserted after the content html
      * `head`: object with sub-entries for all content belonging in the head:
        * `js_vendor_urls`: list of vendor JS file URLs to be loaded in, basically all vendor `<script src="..."` from the `<head>` tag of that page
        * `js_urls`: list of JS file URLs to be loaded in, basically all non-vendor `<script src="..."` from the `<head>` tag of that page. these should be loaded third, after first the `js_vendor_urls``, and then the `scripts` JS have been loaded
        * `css_urls`: list of CSS file URLs to be loaded in, basically all stylesheets from the `<head>` tag of that page
        * `meta`: add all meta tags from the head
        * `styles`: a list of strings of literal inline styles to be inserted before the HTML content is inserted
      * `script_constants`: a list of literal inline JS code that has JS global definitions that need to be loaded before the `js_urls` are inserted (but can be loaded after `js_vendor_urls` are inserted)
      * `scripts`: a list of strings of literal inline JS script code to be executed before (after?) the HTML content is inserted
      * `head_scripts` a list of strings of mixed content of either a single URL of a src JS file (starting with "http") or inline JS code (from within the <head>)
      * `body_scripts` a list of strings of mixed content of either a single URL of a src JS file (starting with "http") or inline JS code (from within the <body>)
      * `sub_navigation`: sidebar content, includes 3 lists: `"sub_navigation" {"top": [...], "middle": [...], "bottom": [...]}`
        * middle is list of the apps that are enabled for the current space
        * each list contains the usual menu items
          * title (will be in current language)
          * url link
          * icon
          * external (bool flag for `target="_blank"`)
        * `sub_navigation` can be `null`, in that case the entire left sidebar is hidden
      * `main_menu`: object with the following sub-entries, signifying how the main dropdown button looks like:
        * `label`: title of the main menu dropdown
        * `icon`: icon of the main menu dropdown, exclusive vs. `main_menu_image`
        * `image`: image of the main menu dropdown, exclusive vs. `main_menu_icon`
      * `announcements`: list of objects that contain data for the announcement banner, if one is active
        * `[]` if None active, else a list `[{"text": "'"<str> Announcement text", "level": "<str> level-code"}, ...]`
        * `level` can take the following values: "debug", "info", "success", "warning", "error". these levels are usually reflected in the color of the announcement background
    """

    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    
    # endpoint param
    url = None
    
    # set during processing
    group = None
    has_leftnav = True  # can be toggled during HTML parsing to determine that this page has no leftnav
    
    # some return values
    content_html = None
    footer_html = None
    main_menu_label = None
    main_menu_icon = None
    main_menu_image = None
    
    _data_proto = {
        "resolved_url": None,
        "redirect": False,
        "status_code": 0,
        "content_html": None,
        "footer_html": None,
        # TODO: decide to keep the following 4 params to deliver JS content or ...
        "js_vendor_urls": [],
        "js_urls": [],
        "script_constants": [],
        "scripts": [],
        # ... or the following 2 params
        "head_scripts": [],
        "body_scripts": [],
        "css_urls": [],
        "meta": None,
        "styles": None,
        "sub_navigation": {},  # can be None if no left navigation should be shown
        "main_menu": {
            "label": None,  # either <name of group>, "personal space", or "community"
            "icon": None,  # exclusive with `main_menu_image`, only one can be non-None!
            "image": None,  # exclusive with `main_menu_icon`, only one can be non-None!
        },
        "announcements": [],
    }
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'url', openapi.IN_QUERY, required=True,
                description='The URL for which the content should be returned.',
                type=openapi.FORMAT_URI
            ),
        ],
        responses={'200': openapi.Response(
            description='WIP: Response info missing. Short example included',
            examples={
                "application/json": {
                    "data": {
                        "resolved_url": "/project/a-mein-bbb-projekt/?force_payment_popup=1",
                        "redirect": False,
                        "status_code": 200,
                        "content_html": "<div class=\"x-v3-container container\"> <div class=\"row app-main\"> ... </div></div>",
                        "footer_html": "<div class=\"footer\"> ... </div>",
                        "js_vendor_urls": [
                            "/static/js/vendor/less.min.js",
                            "/static/js/vendor/jquery-2.1.0.min.js",
                        ],
                        "js_urls": [
                            "http://localhost:8000/static/js/cosinnus.js?v=1.9.3",
                            "http://localhost:8000/static/js/client.js?v=1.9.3",
                        ],
                        "css_urls": [
                            "/static/css/select2.css",
                            "/static/css/extra.css",
                        ],
                        "script_constants": "var cosinnus_base_url = \"http://localhost:8000/\";\nvar cosinnus_active_group = \"a-mein-bbb-projekt\";\n ...",
                        "scripts": "Backbone.mediator.publish('init:module-full-routed', ...",
                        "head_scripts": [
                            "/static/js/vendor/less.min.js",
                            "var cosinnus_base_url = \"http://localhost:8000/\";\nvar cosinnus_active_group = \"a-mein-bbb-projekt\";\n ..."
                        ],
                        "body_scripts": [
                            "http://localhost:8000/static/js/cosinnus.js?v=1.9.3",
                            "Backbone.mediator.publish('init:module-full-routed', ...",
                        ],
                        "meta": "<meta charset=\"utf-8\"/><meta content=\"IE=edge\" http-equiv=\"X-UA-Compatible\"/><meta content=\"width=device-width, initial-scale=1\" name=\"viewport\"/> ...",
                        "styles": ".my-contribution-badge {min-width: 50px;border-radius: 20px;color: #FFF;font-size: 12px;padding: 2px 6px; margin-left: 5px;}.my-contribution-badge.red {background-color: rgb(245, 85, 0);} ...",
                        "sub_navigation": {
                            "top": [
                                {
                                    "id": "Sidebar-pws2dgLA",
                                    "icon": "fa-lightbulb-o",
                                    "label": "Microsite",
                                    "url": "/project/a-mein-bbb-projekt/microsite/",
                                    "is_external": FONT_AWESOME_CLASS_FILTER,
                                    "image": None,
                                    "badge": None
                                }
                            ],
                            "middle": [
                                {
                                    "id": "Sidebar-FTZD61ZZ",
                                    "icon": "fa-th-large",
                                    "label": "Projektdashboard",
                                    "url": "/project/a-mein-bbb-projekt/?browse=true",
                                    "is_external": False,
                                    "image": None,
                                    "badge": None
                                },
                            ],
                            "bottom": [
                                {
                                    "id": "Sidebar-6vcO7aYp",
                                    "icon": "fa-cogs",
                                    "label": "Einstellungen",
                                    "url": "/project/a-mein-bbb-projekt/edit/",
                                    "is_external": False,
                                    "image": None,
                                    "badge": None
                                },
                            ]
                        },
                        "main_menu": {
                            "label": "A Mein BBB Projekt",
                            "icon": None,
                            "image": "/media/cosinnus_portals/portal_saschas_local_dev/avatars/group/xj1VxzF3viA4.jpg"
                        },
                        "announcements": [{
                            "text": "This is an example announcement",
                            "level": "warning"
                        }],
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        self.url = request.query_params.get('url', '').strip()
        self.url = remove_url_param(self.url, 'v', '3')
        django_request = copy(request._request)
        if not self.url:
            raise ValidationError('Missing required parameter: url')
        if not self.url.startswith('http'):
            if not self.url.startswith('/'):
                self.url = '/' + self.url
            self.url = CosinnusPortal.get_current().get_domain() + self.url

        # check if the target URL is one exempted for v3 frontend resolution - we do not accept those
        matched_exemption = False
        target_url_path = urlparse(self.url).path
        # append slash since with a missing resolver it wouldn't be auto appended and might miss matches
        if not target_url_path.endswith('/'):
            target_url_path += '/'
        for url_pattern in settings.COSINNUS_V3_FRONTEND_EVERYWHERE_URL_PATTERN_EXEMPTIONS:
            if re.match(url_pattern, target_url_path):
                matched_exemption = True
                break
        if matched_exemption:
            return self.build_redirect_response(self.url, response=None)

        # resolve the response, including redirects
        # add the v3-exempt parameter to the URL so we do not actually parse the v3-served response
        v3_exempted_url = add_url_param(self.url, FrontendMiddleware.param_key_exempt, FrontendMiddleware.param_value_exempt)
        response = self._resolve_url_via_query(v3_exempted_url, django_request, allow_redirects=False)
        # if we have been redirected, return an empty data package with a redirect target url!
        if response.status_code in [301, 302]:
            # remove the v3-exempt parameter from the resolved URL again
            redirect_target_url = remove_url_param(response.headers["Location"], FrontendMiddleware.param_key_exempt, FrontendMiddleware.param_value_exempt)
            return self.build_redirect_response(redirect_target_url, response)
        
        # fake our django request to act as if the resolved url was the original one
        django_request = self._transform_request_to_resolved(django_request, response.url)
        # get the relative resolved url from the target url (following all redirects)
        resolved_url = django_request.path
        if django_request.GET:
            resolved_url += '?' + django_request.GET.urlencode()
            # remove the v3-exempt parameter from the resolved URL again
            resolved_url = remove_url_param(self.url, FrontendMiddleware.param_key_exempt, FrontendMiddleware.param_value_exempt)
        # remove domain from resolved url
        resolved_url = '/' + '/'.join(resolved_url.split('/')[3:])

        # determine group for request
        self._resolve_request_group(resolved_url, django_request)
        # parse the response's html
        html = self._clean_response_html(str(response.text))

        # TODO compress html? or do server-side request compression?
        
        html_soup = BeautifulSoup(html, 'html.parser')
        parsed_js_urls = self._parse_js_urls(html_soup)
        js_vendor_urls = [js_url for js_url in parsed_js_urls if '/vendor/' in js_url]
        js_urls = [js_url for js_url in parsed_js_urls if '/vendor/' not in js_url]
        css_urls = self._parse_css_urls(html_soup)
        script_constants = self._parse_inline_tag_contents(html_soup, 'script', class_="v3-constants")
        scripts = self._parse_inline_tag_contents(html_soup, 'script', class_=False)
        meta = self._parse_tags(html_soup, 'meta')
        styles = self._parse_inline_tag_contents(html_soup, 'style')
        sub_navigation = self._parse_leftnav_menu(html_soup)
        
        head_scripts = self._parse_js_scripts_and_inlines(html_soup, 'head')
        body_scripts = self._parse_js_scripts_and_inlines(html_soup)
        # filtering the body scripts by the 'body' tag seems to not find all scripts, so we
        # instead find *all* scripts and subtract the ones found in the header
        body_scripts = [body_script for body_script in body_scripts if not body_script in head_scripts]
        
        html_soup = self._filter_html_view_specific(html_soup, resolved_url)
        self._parse_html_content(html_soup) # this will destroy the soup, so use it last or on a new soup!
        
        data = copy(self._data_proto)
        data["resolved_url"] = resolved_url
        data["redirect"] = False
        data["status_code"] = response.status_code
        data["content_html"] = self.content_html
        data["footer_html"] = self.footer_html
        # TODO: decide to keep the following 4 params to deliver JS content or ...
        data["js_vendor_urls"] = js_vendor_urls
        data["js_urls"] = js_urls
        data["script_constants"] = script_constants
        data["scripts"] = scripts
        # ... or the following 2 params
        data["head_scripts"] = head_scripts
        data["body_scripts"] = body_scripts
        data["css_urls"] = css_urls
        data["meta"] = meta
        data["styles"] = styles
        data["sub_navigation"] = sub_navigation  # can be None if no left navigation should be shown
        data["main_menu"] = {
            "label": self.main_menu_label,  # either <name of group>, "personal space", or "community"
            "icon": self.main_menu_icon,  # exclusive with `main_menu_image`, only one can be non-None!
            "image": self.main_menu_image,  # exclusive with `main_menu_icon`, only one can be non-None!
        }
        data["announcements"] = self._get_announcements(django_request)
        
        # set cookies on rest response from the requests response
        # note: we seem to be losing all meta-infos like max-age here,
        #   but none of the cookies returned through this endpoint should be relevant for this.
        return self.build_data_response(data, response)
    
    def build_data_response(self, data, resolved_response=None):
        """ Build a response from the given data package and set the cookies from the resolved target URL query. """
        rest_response = Response(data)
        if resolved_response is not None:
            for k, v in resolved_response.cookies.items():
                rest_response.set_cookie(k, v)
        return rest_response
    
    def build_redirect_response(self, target_url, resolved_response=None):
        """ Builds an empty data package with the `redirect` flag set to True and
            `resolved_url` set to the target redirect URL. """
        data = copy(self._data_proto)
        data["resolved_url"] = target_url
        data["redirect"] = True
        data["status_code"] = resolved_response.status_code
        return self.build_data_response(data, resolved_response)
    
    def _resolve_url_via_query(self, url, request, allow_redirects=True):
        """ Resolves the URL via a requests get().
            Cookies from all redirect steps are passed along collectively. """
        session = requests.Session()
        session.headers.update(dict(request.headers))
        session.cookies.update(request.COOKIES)
        response = session.get(url, allow_redirects=allow_redirects)
        for history_response in response.history:
            response.cookies.update(history_response.cookies)
        return response
    
    def _transform_request_to_resolved(self, request, url):
        """ Fake a given request with a new given url so that it seems that the request aimed
            at the given url. """
        parsed = urlparse(url)
        path = parsed.path
        query = parsed.query
        # fudge request to act like the client sent it to the given URL
        request.path = path
        request.path_info = path
        request.resolver_match
        request.GET = QueryDict(query)
        request.META['PATH_INFO'] = path
        request.META['QUERY_STRING'] = query
        request.environ['PATH_INFO'] = path
        request.environ['QUERY_STRING'] = query
        return request
    
    def _clean_response_html(self, html):
        html = html.replace('\t', '')
        html = re.sub(r'[ \t]+', ' ', html)
        return html
    
    def _resolve_request_group(self, url, request):
        """ Determine and set the group for the request via the resolved group and url
            and also set properties like main menu label and icon depending on this.
            Sets:
                - self.main_menu_label
                - self.main_menu_icon
                - self.main_menu_image
        """
        try:
            # resolve the group if the requested view is part of one
            group_name = url.split('/')[2]
            self.group = get_group_for_request(group_name, request, fail_silently=True)
        except:
            # this catches short URLs and the Http404 that `get_group_for_request` raised when no group is found
            self.group = None
        
        # determine menu labels/image
        if self.group:
            if self.group.is_forum_group or self.group.is_events_group:
                self.main_menu_label = _('Community')
            else:
                self.main_menu_label = self.group['name']
            if self.group.avatar_url:
                self.main_menu_image = self.group.get_avatar_thumbnail_url()
            else:
                self.main_menu_icon = self.group.trans.ICON
        elif any(url.startswith(prefix) for prefix in V3_CONTENT_COMMUNITY_URL_PREFIXES):  # TODO: other places that belong to Community?
            self.main_menu_label = _('Community')
            self.main_menu_icon = 'fa-sitemap'  # TODO: icon for Community space?
        else:
            self.main_menu_label = _('Personal')
            self.main_menu_icon = 'fa-user'  # TODO: icon for Personal space? use user avatar if they have one instead?
    
    def _filter_html_view_specific(self, html_soup, resolved_url):
        """ Will alter the given html soup by specific, hardcoded view/url/page rules,
            for fine-grained control on hiding/modifying elements when displayed in the main content view """
        # remove params from url for matching
        url = remove_url_param(self.url, None, None)
        if self.group:
            # hide appsmenu on specific group pages
            hide_appsmenu_patterns = [
                r"^/(?P<group_type>[^/]+)/(?P<group_slug>[^/]+)/$", # group dashboard page
                r"^/(?P<group_type>[^/]+)/(?P<group_slug>[^/]+)/microsite/$", # group  microsite
            ]
            if any([re.match(pattern, resolved_url) for pattern in hide_appsmenu_patterns]):
                appsmenu_tag = html_soup.find('div', class_='x-v3-leftnav')
                if appsmenu_tag:
                    appsmenu_tag.decompose()
            # do not display group dashboard tiles
            hide_dashboard_tiles_patterns = [
                r"^/(?P<group_type>[^/]+)/(?P<group_slug>[^/]+)/$",  # group dashboard page
            ]
            if any([re.match(pattern, resolved_url) for pattern in hide_dashboard_tiles_patterns]):
                tile_tags = html_soup.find_all('div', class_='dashboard-header-link')
                for tile_tag in tile_tags:
                    tile_tag.decompose()
            
        return html_soup
    
    def _parse_html_content(self, destructible_html_soup):
        """ Parses the content frame of the full html that can be put into any other part of the site.
            May do some reformatting for full-page views to transform the body tag into a div.
            Also parses the footer html content.
            Sets:
                - self.has_leftnav
                - self.content_html
                - self.footer_html
            Note: this will permanently alter the soup given! """
        soup = destructible_html_soup
        # remove all tags we never want to see in the content, like inline scripts and styles
        for bad_tag_literal in ['nav', 'script', 'style']:
            for bad_tag in soup.find_all(bad_tag_literal):
                bad_tag.decompose()
        # try to extract our page's inner container, below the breadcrumb
        content = soup.find('div', class_='x-v3-content')
        if not content:
            # if that doesn't exist, try to extract the
            content = soup.find('div', class_='x-v3-container')
        if not content:
            # if even that doesn't exist, return the content of the body tag, minus all <nav> tags
            content = soup.find('body')
            content = content.decode_contents()
            self.has_leftnav = False
        self.content_html = str(content or '').strip()
        footer = soup.find('div', class_='x-v3-footer')
        if footer:
            self.footer_html = str(footer.decode_contents()).strip()
    
    def _extract_fa_icon(self, tag):
        """ Extracts the actual font-awesome icon class name from the first i tag within the given tag tree """
        fa_class = 'fa-group' # fallback for icons that do not have one
        # TODO: add a better fallback! for example http://localhost:8000/api/v3/content/main/?url=http://localhost:8000/group/forum/event/list/
        # on the leftnav is missing icons for links with numbers in them!
        fa_i = tag.find('i')
        if fa_i:
            fa_class = ' '.join([subclass for subclass in fa_i.get('class') if not subclass.lower() in FONT_AWESOME_CLASS_FILTER])
        return fa_class
        
    def _parse_leftnav_menu(self, html_soup):
        """ Tries to parse from the leftnav all links to show in the left sub navigation.
            Can return None"""
        if not self.has_leftnav:
            return None
        leftnav = html_soup.find('div', class_='x-v3-leftnav')
        if not leftnav:
            self.has_leftnav = False
            return None
        
        top = []
        middle = []
        bottom = []
        
        # extract appsmenu links (<a>) AND leftnav elements (<button>) from the leftnav,
        # because the beautifulsoup filters apply to both
        for leftnav_link in leftnav.find_all(['a', 'button']):
            # skip link-less buttons (like the dropdown trigger)
            href = leftnav_link.get('href')
            if not href or href == '#':
                continue
            link_label = '(Link)'
            text_source = leftnav_link.find('div', class_='media-body') or leftnav_link
            if text_source:
                link_label = text_source.text.strip().replace('/n', '')
            # create menu item for the link
            menu_item = MenuItem(
                link_label,
                href,
                icon=self._extract_fa_icon(leftnav_link),  # TODO. filter/map-convert these icons to frontend icons?
                id='Sidebar-' + get_random_string(8),
            )
            # select the proper subnav for this menu to go to, by type of URL
            target_subnav = middle
            if any(menu_item['url'].endswith(suffix) for suffix in V3_CONTENT_BOTTOM_SIDEBAR_URL_SUFFIXES):
                target_subnav = bottom
            elif any(menu_item['url'].endswith(suffix) for suffix in V3_CONTENT_TOP_SIDEBAR_URL_SUFFIXES):
                target_subnav = top
            target_subnav.append(menu_item)
        
        # add sidebar third party tools if it exists in group data
        if self.group and self.group.third_party_tools:
            for third_party_tool in self.group.third_party_tools:
                try:
                    middle.append(MenuItem(
                        third_party_tool['label'],
                        third_party_tool['url'],
                        icon='fa-external-link',
                        id='Sidebar-Thirdparty-' + get_random_string(8),
                        is_external=True
                    ))
                except Exception as e:
                    logger.warning('Error converting a thirdparty group menu item to MenuItem', extra={'exc': e})
        
        sub_nav = {
            "top": top,
            "middle": middle,
            "bottom": bottom,
        }
        return sub_nav
    
    def _parse_css_urls(self, html_soup):
        css_links = html_soup.find_all('link', rel='stylesheet')
        css_urls = [link.get('href') for link in css_links]
        css_urls = [self._format_static_link(link) for link in css_urls]
        css_urls = uniquify_list(css_urls)
        return css_urls
    
    def _parse_js_urls(self, html_soup):
        # this
        js_links = html_soup.find_all('script', src=True)
        js_urls = [link.get('src') for link in js_links]
        js_urls = [self._format_static_link(link) for link in js_urls]
        js_urls = uniquify_list(js_urls)
        return js_urls
    
    def _parse_tags(self, html_soup, tag_name):
        """ Parses all tags of a given tag name and returns them, including their tag definition,
            as a concatenated string """
        tags = html_soup.find_all(tag_name)
        tag_str = '\n'.join([str(tag).strip() for tag in tags])
        return tag_str
    
    def _parse_inline_tag_contents(self, html_soup, tag_name, class_=False):
        """ Parses all contents of tags of a given tag name and returns it as a concatenated string """
        # and this
        tags = html_soup.find_all(tag_name, src=False, rel=False, class_=class_)
        liss = [tag.decode_contents().strip() for tag in tags]
        tag_contents = '\n'.join(liss)
        return tag_contents
    
    def _parse_js_scripts_and_inlines(self, html_soup, container_tag_name=None):
        """ Parses from the given soup both script sources and inline scripts.
            @param container_tag_name: if given, searches for scripts only within this tag name (e.g. "body")
            @return a list of strings, mixed content of either:
                - a single URL of a src JS file (starting with "http") or
                - inline JS code
        """
        js_list = []
        container_tag = html_soup.find(container_tag_name) if container_tag_name else html_soup
        script_elements = container_tag.find_all('script')
        for tag in script_elements:
            js_link = tag.get('src')
            if js_link:
                # we have a JS file link by src
                js_list.append(self._format_static_link(js_link))
            else:
                # we have an inline script
                inline_script_content = tag.decode_contents().strip()
                js_list.append(inline_script_content)
        return js_list
    
    def _format_static_link(self, link):
        domain = CosinnusPortal.get_current().get_domain()
        link = (domain if not link.startswith('http') else '') + link
        if '?v=' in link:
            link = link[:link.find('?v=')]
        return link
        
    def _get_announcements(self, request):
        announcements = []
        for announcement in Announcement.objects.active():
            announcements.append({
                "text": announcement.translated_text or announcement.text,
                "level": announcement.level,
            })
        # check extra email-verified and guest user announcements
        context = email_verified_context_processor(request)
        if 'email_not_verified_announcement' in context:
            announcements.append(context['email_not_verified_announcement'])
        if 'user_guest_announcement' in context:
            announcements.append(context['user_guest_announcement'])
        return announcements
    