import requests
import logging


class SonosInterface:
    def __init__(self, url, zone, queuemode):
        self.url = url
        self.zone = zone
        self.queuemode = queuemode

    def set_track(self,track_id):
        if isinstance(track_id,str):
            r = requests.get(self.url + '/' + self.zone + '/spotify/' + self.queuemode + '/spotify:track:' + track_id)
            logging.debug('Request: ' + r.text)
            if r.status_code == 200:
                return True
            else:
                return False
        else:
            logging.debug('Invalid track')
            return False

    def set_queue_mode(self,mode):
        self.queuemode = mode
        return self.queuemode

    def get_queue_mode(self):
        return self.queuemode
