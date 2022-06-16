from typing import Optional

from sqlmodel import Field, SQLModel, create_engine, Session


class Tracks(SQLModel, table=True):
    key: str
    track_name: Optional[str] = None
    artist_name: Optional[str] = None
    spotify_id: str


engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)

def set_track(track_name: str, artist_name: str, spotify_id: str):
    with Session(engine) as session:
        track = Tracks(track_name=track_name, artist_name=artist_name, spotify_id=spotify_id)
        session.add(track)
        session.commit()

def get_track_id(key: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            return track.spotify_id
        else:
            return None

def delete_track(key: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            session.delete(track)
            session.commit()