# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import urlparse

from cosinnus.conf import settings

from requests_oauthlib import OAuth1Session
from requests_oauthlib import OAuth1


# this is mostly from: http://requests-oauthlib.readthedocs.io/en/latest/oauth1_workflow.html


def do_oauth1_request(request):
    """ Gets a initial OAuth temporary token and secret and saves them in the session and returns the redirect URL for the user.
        @return: The authorization URL on the OAuth server app to send to user to for the authorization
        @raise TokenRequestDenied: can't access request URL or another error like mismatching signature
        @raise ConnectionError: wrong URL """
    
    # Using OAuth1Session
    oauth = OAuth1Session(
        settings.COSINNUS_SSO_OAUTH_CLIENT_KEY,
        client_secret=settings.COSINNUS_SSO_OAUTH_CLIENT_SECRET,
        callback_uri=settings.COSINNUS_SSO_OAUTH_CALLBACK_URL,
    )
    
    fetch_response = oauth.fetch_request_token(settings.COSINNUS_SSO_OAUTH_REQUEST_URL)
    
    # save temporary oauth_token and secret to session and 
    temp_oauth_token = fetch_response.get('oauth_token')
    temp_oauth_secret = fetch_response.get('oauth_token_secret')
    request.session['temp_oauth_token'] = temp_oauth_token
    request.session['temp_oauth_secret'] = temp_oauth_secret
    
    user_authorization_url = oauth.authorization_url(settings.COSINNUS_SSO_OAUTH_AUTHORIZATION_URL)
    
    return user_authorization_url
    

def do_oauth1_receive(request):
    """ Receives the redirected request after the user authorized the oauth handshake at the OAuth server.
        Afterwards, it immediately uses the key to access the user account infos.
        @return: A dictionary with user infos and the permanent oauth_token and oauth_secret for that user """ 
    
    if not 'oauth_token' in request.GET or not 'oauth_verifier' in request.GET:
        raise Exception('Handle me: oauth redirect params were missing!')
    temp_oauth_token = request.GET.get('oauth_token')
    verifier = request.GET.get('oauth_verifier')
    
    session_temp_oauth_token = request.session.get('temp_oauth_token')
    # check if temp_oauth_token matches the one in the session to check if this user initiated the handshake
    if session_temp_oauth_token != temp_oauth_token:
        raise Exception('Handle me: oauth temporary token did not match that in the session!')
    # get temp oauth_secret from the session
    temp_oauth_secret = request.session.get('temp_oauth_secret')
    
    oauth = OAuth1Session(
        settings.COSINNUS_SSO_OAUTH_CLIENT_KEY,
        client_secret=settings.COSINNUS_SSO_OAUTH_CLIENT_SECRET,
        resource_owner_key=temp_oauth_token,
        resource_owner_secret=temp_oauth_secret,
        verifier=verifier)
    oauth_tokens = oauth.fetch_access_token(settings.COSINNUS_SSO_OAUTH_ACCESS_URL)
    oauth_token = oauth_tokens.get('oauth_token')
    oauth_secret = oauth_tokens.get('oauth_token_secret')
    
    
    # access user info on server with those tokens
    oauth = OAuth1Session(settings.COSINNUS_SSO_OAUTH_CLIENT_KEY,
                          client_secret=settings.COSINNUS_SSO_OAUTH_CLIENT_SECRET,
                          resource_owner_key=oauth_token,
                          resource_owner_secret=oauth_secret)
    user_request = oauth.get(settings.COSINNUS_SSO_OAUTH_CURRENT_USER_ENDPOINT_URL)
    
    # return user info and permanent oauth tokens
    user_info = user_request.json()
    user_info.update({
        'oauth_token': oauth_token,
        'oauth_secret': oauth_secret,            
    })
    return user_info

