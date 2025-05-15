import requests

from cosinnus.conf import settings


class DeckConnection:
    BASE_URL = f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/index.php/apps/deck'
    HEADERS = {'OCS-APIRequest': 'true', 'Accept': 'application/json'}
    API_PARAMS = {'auth': settings.COSINNUS_CLOUD_NEXTCLOUD_AUTH, 'headers': HEADERS}

    def _api_get(self, url):
        return requests.get(self.BASE_URL + url, **self.API_PARAMS)

    def _api_post(self, url, data):
        return requests.post(self.BASE_URL + url, data=data, **self.API_PARAMS)

    def _api_put(self, url, data):
        return requests.put(self.BASE_URL + url, data=data, **self.API_PARAMS)

    def board_create(self, title):
        """TODO"""
        board_id = None
        data = {
            'title': title,
            'color': 'ffffff',
        }
        response = self._api_post('/boards', data=data)
        if response.status_code == 200:
            try:
                response_json = response.json()
                board_id = response_json.get('id')
            except Exception:
                pass
        if not board_id:
            # TODO raise exception
            print(response)
            pass
        return board_id

    def board_update(self, board_id, title, archived=False):
        """TODO"""
        data = {
            'title': title,
            'archived': 1 if archived else 0,
            'color': 'ffffff',
        }
        response = self._api_put(f'/boards/{board_id}', data=data)
        if response.status_code != 200:
            # TODO: log and raise error
            print(response)
            pass

    def board_add_group_access(self, board_id, group_id):
        """TODO"""
        # TODO: resending returns 500, check for group update
        data = {
            'type': 1,
            'participant': group_id,
            'permissionEdit': 1,
            'permissionShare': 1,
            'permissionManage': 0,
        }
        response = self._api_post(f'/boards/{board_id}/acl', data=data)
        if response.status_code == 500:
            # TODO: check if already exists, if not raise error
            print(response)
            pass
        elif response.status_code != 200:
            # TODO: raise error
            print(response)
            pass
