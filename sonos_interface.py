import logging
from urllib.parse import quote

import httpx


class SonosInterface:
    def __init__(self, url, zone, queuemode, queueclear):
        self.url = url.rstrip("/")
        self.zone = zone
        self.queuemode = queuemode
        self.queueclear = queueclear
        self.client = httpx.AsyncClient(timeout=10.0)

    def _url(self, *parts):
        path = "/".join(quote(str(part), safe=":") for part in parts)
        return f"{self.url}/{path}"

    async def _get(self, *parts):
        try:
            response = await self.client.get(self._url(self.zone, *parts))
            logging.debug("Request: " + response.text)
            return response
        except httpx.HTTPError as e:
            logging.error(f"Sonos API request failed: {e}")
            return None

    async def close(self):
        await self.client.aclose()

    async def set_track(self,track_id):
        if isinstance(track_id,str):
            if not await self.is_playing():
                if self.queueclear:
                    await self.clearQueue()
            r = await self._get("spotify", self.queuemode, "spotify:track:" + track_id)
            if not await self.is_playing():
                await self.play()

            if r and r.status_code == 200:
                return True
            else:
                return False
        else:
            logging.error('Invalid track')
            return False

    async def is_playing(self):
        r = await self._get("state")
        if r and r.status_code == 200:
            return r.json().get('playbackState') == 'PLAYING'
        return False

    async def play(self):
        r = await self._get("play")
        if r and r.status_code == 200:
            return True
        else:
            return False

    async def clearQueue(self):
        r = await self._get("clearqueue")
        if r and r.status_code == 200:
            return True
        else:
            return False

    def set_queue_mode(self,mode):
        self.queuemode = mode
        return self.queuemode

    def get_queue_mode(self):
        return self.queuemode
