from asyncio.log import logger
from typing import Optional
import logging

from sqlmodel import Field, SQLModel, create_engine, Session


class Tracks(SQLModel, table=True):
    key: str = Field(primary_key=True)
    track_name: Optional[str] = None
    artist_name: Optional[str] = None
    spotify_id: str


engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)

def set_track(key: str, track_name: str, artist_name: str, spotify_id: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            logging.debug(f'Track already exists for key {key}. Updating fields')
            track.track_name = track_name
            track.artist_name = artist_name
            track.spotify_id = spotify_id
        else:
            logging.debug(f'Creating new track in database for {key}')
            track = Tracks(key=key, track_name=track_name, artist_name=artist_name, spotify_id=spotify_id)
            session.add(track)
        session.commit()

def get_track_id(key: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            logging.debug(f'Track found in database: {track.spotify_id}')
            return track.spotify_id 
        else:
            logging.error(f'No track found for key {key}')
            return None

def delete_track(key: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            logging.debug(f'Deleting track from database: {track.spotify_id}')
            session.delete(track)
            session.commit()
        else:
            logging.error(f'No track found for key {key}')
            return None