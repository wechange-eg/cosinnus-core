# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from requests_oauthlib import OAuth1Session

import requests
from requests_oauthlib import OAuth1

from urlparse import parse_qs



# this is mostly from: http://requests-oauthlib.readthedocs.io/en/latest/oauth1_workflow.html

# ################## INTO SETTINGS.py ############

# this comes from the configured OAuth application in /wp-admin/users.php?page=rest-oauth1-apps
# these MUST MATCH the settings there exactly!
client_key = 'DUgGz0rOabZZ'
client_secret = 'UR7nPfG8oQDEwHLlQfPLSWcxyBSGWIcLC3p3V5q3tdMG03xE'
callback_uri = 'http://localhost/cb/'

request_token_url = 'http://vca.sinnwerkstatt.com/oauth1/request'
authorization_url = 'http://vca.sinnwerkstatt.com/oauth1/authorize'
access_url = 'http://vca.sinnwerkstatt.com/oauth1/access'

#########################

"""
from cosinnus.utils.oauth import do_oauth_request; do_oauth_request()
"""

# step 1
def do_oauth_request():
    """ Gets the initial OAuth temporary token
        @return: The authorization URL to send the user to 
        @raise TokenRequestDenied: can't access request URL or another error like mismatching signature
        @raise ConnectionError: wrong URL """
    
    
    # Using OAuth1Session
    oauth = OAuth1Session(
        client_key,
        client_secret=client_secret,
        callback_uri=callback_uri,
    )
    fetch_response = oauth.fetch_request_token(request_token_url)
    {
        "oauth_token": "Z6eEdO8MOmk394WozF5oKyuAv855l4Mlqo7hhlSLik",
        "oauth_token_secret": "Kd75W4OQfb2oJTV0vzGzeXftVAwgMnEK9MumzYcM"
    }
    resource_owner_key = fetch_response.get('oauth_token')
    resource_owner_secret = fetch_response.get('oauth_token_secret')
    
    print "> owner key, secret", resource_owner_key, resource_owner_secret
    
    user_authorization_url = oauth.authorization_url(authorization_url)
    
    print ">> returning URL", user_authorization_url
    return user_authorization_url

"""
def do_oauth_request_WITH_HELPER():
    # Using OAuth1 auth helper
    oauth = OAuth1(client_key, client_secret=client_secret)
    r = requests.post(url=request_token_url, auth=oauth)
    print ">> conty", r.content
    #"oauth_token=Z6eEdO8MOmk394WozF5oKyuAv855l4Mlqo7hhlSLik&oauth_token_secret=Kd75W4OQfb2oJTV0vzGzeXftVAwgMnEK9MumzYcM"
    from urlparse import parse_qs
    credentials = parse_qs(r.content)
    resource_owner_key = credentials.get('oauth_token')[0]
    resource_owner_secret = credentials.get('oauth_token_secret')[0]
    
    authorize_url = authorization_url + '?oauth_token='
    authorize_url = authorize_url + resource_owner_key
    print 'Please go here and authorize,', authorize_url
"""
    
if __name__ == "__main__":
    do_oauth_request()
    #do_oauth_request_WITH_HELPER()
