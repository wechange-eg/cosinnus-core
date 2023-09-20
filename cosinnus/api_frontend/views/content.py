import re
from copy import copy
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from django.http import QueryDict, Http404
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from announcements.models import Announcement
from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.conf import settings
from cosinnus.core.decorators.views import get_group_for_request
from cosinnus.models import CosinnusPortal
from cosinnus.models.user_dashboard import MenuItem, FONT_AWESOME_CLASS_FILTER
from cosinnus.utils.http import remove_url_param

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
    """
    An endpoint that returns HTML content for any legacy view on the portal.
    
    Return values:
      * `resolved_url`: the resolved URL after following all redirects the queried `url` parameter might have caused, and the actual URL from which the content HTML is delivered
      * `status_code`: (int), HTTP status code of the response for the request sent to the `resolved_url`
      * `content_html`: html from the `<div class="container">` frame to be inserted
      * `footer_html`: html from the footer, to be inserted after the content html
      * `head`: object with sub-entries for all content belonging in the head:
        * `js_urls`: list of JS file URLs to be loaded in, basically all `<script src="..."` from the `<head>` tag of that page
        * `css_urls`: list of CSS file URLs to be loaded in, basically all stylesheets from the `<head>` tag of that page
        * `meta`: add all meta tags from the head
        * `styles`: a list of strings of literal inline styles to be inserted before the HTML content is inserted
      * `scripts`: a list of strings of literal inline JS script code to be executed before (after?) the HTML content is inserted
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
                        "status_code": 200,
                        "content_html": "<div class=\"x-v3-container container\"> <div class=\"row app-main\"> ... </div></div>",
                        "footer_html": "<div class=\"footer\"> ... </div>",
                        "js_urls": [
                            "/static/js/vendor/less.min.js",
                            "/static/js/vendor/jquery-2.1.0.min.js",
                        ],
                        "css_urls": [
                            "/static/css/select2.css",
                            "/static/css/extra.css",
                        ],
                        "scripts": "var cosinnus_base_url = \"http://localhost:8000/\"; var cosinnus_active_group = \"a-mein-bbb-projekt\";  ...",
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
        
        # resolve the response, including redirects
        response = self._resolve_url_via_query(self.url, django_request)
        # fake our django request to act as if the resolved url was the original one
        django_request = self._transform_request_to_resolved(django_request, response.url)
        # get the relative resolved url from the target url (following all redirects)
        resolved_url = django_request.path
        if django_request.GET:
            resolved_url += '?' + django_request.GET.urlencode()
        # determine group for request
        self._resolve_request_group(resolved_url, django_request)
        # parse the response's html
        html = self._clean_response_html(str(response.text))
        self._parse_html_content(html)
        
        # TODO compress html? or do server-side request compression?
        
        data = {
            "resolved_url": resolved_url,
            "status_code": response.status_code,
            "content_html": self.content_html,
            "footer_html": self.footer_html,
            "js_urls": self._parse_js_urls(html),
            "css_urls": self._parse_css_urls(html),
            "scripts": self._parse_inline_tag_contents(html, 'script'),
            "meta": self._parse_tags(html, 'meta'),
            "styles": self._parse_inline_tag_contents(html, 'style'),
            "sub_navigation": self._parse_leftnav_menu(html),  # can be None if no left navigation should be shown
            "main_menu": {
                "label": self.main_menu_label,  # either <name of group>, "personal space", or "community"
                "icon": self.main_menu_icon,  # exclusive with `main_menu_image`, only one can be non-None!
                "image": self.main_menu_image,  # exclusive with `main_menu_icon`, only one can be non-None!
            },
            "announcements": self._get_announcements(),
        }
        
        # set cookies on rest response from the requests response
        # note: we seem to be losing all meta-infos like max-age here,
        #   but none of the cookies returned through this endpoint should be relevant for this.
        rest_response = Response(data)
        for k, v in response.cookies.items():
            rest_response.set_cookie(k, v)
        
        # TODO: set headers as well?
        
        return rest_response
    
    def _resolve_url_via_query(self, url, request):
        """ Resolves the URL via a requests get().
            Cookies from all redirect steps are passed along collectively. """
        session = requests.Session()
        session.headers.update(dict(request.headers))
        session.cookies.update(request.COOKIES)
        response = session.get(url)
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
        html = html.replace('\t', '').replace('\n', '')
        html = re.sub(r'\s+', ' ', html)
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
        
    def _parse_html_content(self, html):
        """ Parses the content frame of the full html that can be put into any other part of the site.
            May do some reformatting for full-page views to transform the body tag into a div.
            Also parses the footer html content. """
        soup = BeautifulSoup(html, 'html.parser')
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
        fa_class = None
        fa_i = tag.find('i')
        if fa_i:
            fa_class = ' '.join([subclass for subclass in fa_i.get('class') if not subclass.lower() in FONT_AWESOME_CLASS_FILTER])
        return fa_class
        
    def _parse_leftnav_menu(self, html):
        """ Tries to parse from the leftnav all links to show in the left sub navigation.
            Can return None"""
        if not self.has_leftnav:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        leftnav = soup.find('div', class_='x-v3-leftnav')
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
            # create menu item for the link
            menu_item = MenuItem(
                leftnav_link.text.strip(),
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
            
        sub_nav = {
            "top": top,
            "middle": middle,
            "bottom": bottom,
        }
        return sub_nav
    
    def _parse_css_urls(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        css_links = soup.find_all('link', rel='stylesheet')
        css_urls = [link.get('href') for link in css_links]
        return css_urls
    
    def _parse_js_urls(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        js_links = soup.find_all('script', src=True)
        js_urls = [link.get('src') for link in js_links]
        return js_urls
    
    def _parse_tags(self, html, tag_name):
        """ Parses all tags of a given tag name and returns them, including their tag definition,
            as a concatenated string """
        soup = BeautifulSoup(html, 'html.parser')
        tags = soup.find_all(tag_name)
        tag_str = ''.join([str(tag).strip() for tag in tags])
        return tag_str
    
    def _parse_inline_tag_contents(self, html, tag_name):
        """ Parses all contents of tags of a given tag name and returns it as a concatenated string """
        soup = BeautifulSoup(html, 'html.parser')
        tags = soup.find_all(tag_name, src=False, rel=False)
        tag_contents = ''.join([tag.decode_contents().strip() for tag in tags])
        return tag_contents
        
    def _get_announcements(self):
        announcements = []
        for announcement in Announcement.objects.active():
            announcements.append({
                "text": announcement.translated_text or announcement.text,
                "level": announcement.level,
            })
        return announcements
    