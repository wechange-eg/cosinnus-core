import logging
import functools
from django.utils.decorators import available_attrs
from cosinnus.conf import settings
import requests
from django.core.cache import cache

logger = logging.getLogger('cosinnus')


STREAM_API_BASE_URL = settings.COSINNUS_CONFERENCES_STREAMING_API_URL
STREAM_API_USER = settings.COSINNUS_CONFERENCES_STREAMING_API_AUTH_USER
STREAM_API_PASSWORD = settings.COSINNUS_CONFERENCES_STREAMING_API_AUTH_PASSWORD

_STREAM_API_ACCESS_TOKEN_CACHE_KEY = 'cosinnus/core/conferences/streaming/access_token'


class StreamAPINotLoggedIn(Exception):
    """ Thrown when the current access token was not valid anymore """
    pass


def _logged_in_stream_request(function):
    """ Wrapper for any function that performs an authentication-required request
        to the stream API, that attempts to make the call, and if not logged in, or
        if the cached access token is no longer valid, gets a fresh access token,
        caches it, and retries the call.
        Use `_stream_api_request()` in the wrapped function to make calls to the streaming API! """
    @functools.wraps(function, assigned=available_attrs(function))
    def wrapper(*args, **kwargs):
        # check if streaming is enabled and all settings are set
        if not settings.COSINNUS_CONFERENCES_STREAMING_ENABLED:
            logger.warn('BBB Streaming: Ignoring a call because streaming is not enabled')
            return None
        if not STREAM_API_BASE_URL or not STREAM_API_USER or not STREAM_API_PASSWORD:
            logger.warn('BBB Streaming: Ignoring a call because of missing API URL/credentials.')
            return None
        
        # check if cached token exists
        try:
            return function(*args, **kwargs)
        except StreamAPINotLoggedIn as e:
            try:
                token = _get_stream_api_access_token()
                if not token:
                    return None
                cache.set(_STREAM_API_ACCESS_TOKEN_CACHE_KEY, token)
            except Exception:
                return None
            try:
                return function(*args, **kwargs)
            except StreamAPINotLoggedIn as e:
                logger.error('BBB Streaming: Obtained access token was not valid.', extra={'exception': e})
                return None
            
    return wrapper


def _get_stream_api_access_token():
    """ Logs in to the streaming API and returns a fresh auth access token. """
    data = {
        "username": STREAM_API_USER,
        "password": STREAM_API_PASSWORD,
    }
    response = requests.post(f'{STREAM_API_BASE_URL}/token/', data=data)
    if response.ok and 'access' in response.json():
        return response.json()['access']
    else:
        logger.error('BBB Streaming: Could not get auth access token!', extra={
            'response_code': response, 'response_text': response.text, 'URL': STREAM_API_BASE_URL})
        return None
    

def _stream_api_request(method, sub_url, data=None):
    """ Calls any supplied request on the Streaming server. Plays nicely
        together with the `_logged_in_stream_request` decorator to signal a 
        fresh login and retry of the request if the current auth token was not valid anymore. """
    auth_token = cache.get(_STREAM_API_ACCESS_TOKEN_CACHE_KEY)
    if auth_token is None:
        raise StreamAPINotLoggedIn()
    
    methods = {
        'get': requests.get,
        'post': requests.post,
        'delete': requests.delete,
    }
    _method = methods.get(method, None)
    if _method is None:
        raise Exception('BBB Streaming: requests method not supported: ' + method)
    headers = {'Content-Type': 'application/json',
           'Authorization': 'Bearer {0}'.format(auth_token)}
    
    response = _method(f'{STREAM_API_BASE_URL}{sub_url}', headers=headers, json=data)
    
    if response.ok:
        return response
    elif response.status_code == 403:
        if response.json().get('code', None) == 'token_not_valid':
            raise StreamAPINotLoggedIn()
    else:
        logger.error(f'BBB Streaming: Request {method}: {sub_url} was not successful!', extra={
            'data': data,
            'url': f'{STREAM_API_BASE_URL}{sub_url}',
            'response_code': response.status_code,
            'response_text': response.text,
        })
        return response


@_logged_in_stream_request
def create_streamer(name, bbb_url, bbb_secret, meeting_id, stream_url):
    """ Creates a streamer on the streaming server. 
        @return: The ID of the created streamer or raises an exception """
    
    data = {
        "name": name,
        "settings": {
            "BBB_URL": bbb_url,
            "BBB_SECRET": bbb_secret,
            "BBB_MEETING_ID": meeting_id, 
            "BBB_STREAM_URL": stream_url,
        }
    }
    response = _stream_api_request('post', '/streamers/', data)
    if response.ok:
        ret_json = response.json()
        if 'id' in ret_json.keys():
            return ret_json.get('id')
        else:
            logger.error('BBB Streaming: Create Streamer call was successful but contained no id in data!', extra={
                'streamer_name': name,
                'ret_json': ret_json,
            })
    raise Exception('BBB Streaming: create_streamer not successful!')
        

@_logged_in_stream_request
def start_streamer(streamer_id):
    """ Starts a streamer by id.
        @return: True of the streamer was started or raises an exception """
    
    response = _stream_api_request('post', f'/streamers/{streamer_id}/start/')
    if response.ok:
        return True
    raise Exception('BBB Streaming: delete_streamer not successful!')


@_logged_in_stream_request
def stop_streamer(streamer_id):
    """ Stops a streamer by id.
        @return: True of the streamer was started or raises an exception """
    
    response = _stream_api_request('post', f'/streamers/{streamer_id}/stop/')
    if response.ok:
        return True
    raise Exception('BBB Streaming: delete_streamer not successful!')

@_logged_in_stream_request
def delete_streamer(streamer_id):
    """ Deletes a streamer by id.
        On success, returns True, on error returns False, meaning the streamer is no
        longer active and can be deleted from our records.
        Raises an exception on other results. 
        @return: True if the streamer was deleted, False if it already didn't exist, otherwise raises an exception """
    
    response = _stream_api_request('delete', f'/streamers/{streamer_id}/')
    if response.ok:
        return True
    elif response.status_code == 404:
        return False
    raise Exception('BBB Streaming: delete_streamer not successful!')

