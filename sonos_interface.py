import logging
import re
from urllib.parse import quote
from urllib.parse import unquote

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
            state = await self.get_state()
            is_playing = self.is_state_playing(state)
            is_queue_playback = await self.is_current_track_in_queue(state)
            is_external_source = not is_queue_playback
            should_clear_queue = self.queueclear and (not is_playing or is_external_source)

            if should_clear_queue:
                await self.clearQueue()

            queue_mode = "now" if self.queueclear and is_external_source else self.queuemode
            r = await self._get("spotify", queue_mode, "spotify:track:" + track_id)
            if not is_playing and queue_mode != "now":
                await self.play()

            if r and r.status_code == 200:
                return True
            else:
                return False
        else:
            logging.error('Invalid track')
            return False

    async def get_state(self):
        r = await self._get("state")
        if r and r.status_code == 200:
            return r.json()
        return None

    def is_state_playing(self, state):
        if state:
            return state.get('playbackState') == 'PLAYING'
        return False

    async def is_playing(self):
        return self.is_state_playing(await self.get_state())

    async def is_current_track_in_queue(self, state=None):
        if state is None:
            state = await self.get_state()

        current_track_id = self.spotify_track_id_from_uri(
            (state or {}).get("currentTrack", {}).get("uri", "")
        )
        if not current_track_id:
            return False

        r = await self._get("queue", "detailed")
        if not r or r.status_code != 200:
            return False

        for queue_item in r.json():
            queue_track_id = self.spotify_track_id_from_uri(queue_item.get("uri", ""))
            if queue_track_id == current_track_id:
                return True

        return False

    def spotify_track_id_from_uri(self, uri):
        decoded_uri = unquote(uri or "")
        match = re.search(r"spotify:track:([^?&]+)", decoded_uri)
        if match:
            return match.group(1)
        return None

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
