import requests
import logging


class SonosInterface:
    def __init__(self, url, zone, queuemode, queueclear):
        self.url = url
        self.zone = zone
        self.queuemode = queuemode
        self.queueclear = queueclear

    def set_track(self,track_id):
        if isinstance(track_id,str):
            if not self.is_playing():
                if self.queueclear:
                    self.clearQueue()
            r = requests.get(self.url + '/' + self.zone + '/spotify/' + self.queuemode + '/spotify:track:' + track_id)
            logging.debug('Request: ' + r.text)
            if not self.is_playing():
                self.play()

            if r.status_code == 200:
                return True
            else:
                return False
        else:
            logging.debug('Invalid track')
            return False

    def is_playing(self):
        r = requests.get(self.url + '/' + self.zone + '/state')
        logging.debug('Request: ' + r.text)
        if r.status_code == 200:
            if r.json()['playbackState'] == 'PLAYING':
                return True
            else:
                return False
        else:
            return False

    def play(self):
        r = requests.get(self.url + '/' + self.zone + '/play')
        logging.debug('Request: ' + r.text)
        if r.status_code == 200:
            return True
        else:
            return False

    def clearQueue(self):
        r = requests.get(self.url + '/' + self.zone + '/clearqueue')
        logging.debug('Request: ' + r.text)
        if r.status_code == 200:
            return True
        else:
            return False

    def set_queue_mode(self,mode):
        self.queuemode = mode
        return self.queuemode

    def get_queue_mode(self):
        return self.queuemode
