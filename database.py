import os
import logging
import configparser
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from sqlalchemy.pool import NullPool

config = configparser.ConfigParser()
config.read('config.ini')

database_path = os.environ.get("DIMEPI_DATABASE_PATH", config['database']['db_path'])

# Check if database file exists
db_exists = os.path.exists(database_path)

class Tracks(SQLModel, table=True):
    key: str = Field(primary_key=True)
    track_name: Optional[str] = None
    artist_name: Optional[str] = None
    spotify_id: str

class Credits(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    credit_count: int

class CabinetLightsSettings(SQLModel, table=True):
    __tablename__ = "cabinet_lights_settings"

    id: Optional[int] = Field(default=1, primary_key=True)
    current_r: int
    current_g: int
    current_b: int
    saved_r: int
    saved_g: int
    saved_b: int
    current_on_time: str
    current_off_time: str
    saved_on_time: str
    saved_off_time: str

engine = create_engine(
    f"sqlite:///{database_path}",
    connect_args={"timeout": 5},
    poolclass=NullPool,
)

# Create any missing tables. Existing tables are left unchanged.
if not db_exists:
    logging.info(f"Database file {database_path} not found. Creating new database and tables.")
else:
    logging.info(f"Database file {database_path} found. Using existing database.")
SQLModel.metadata.create_all(engine)

###################################################################################
#################### Functions for managing tracks ################################
###################################################################################

def normalize_key(key: str):
    return key.strip().upper()

def set_track(key: str, track_name: str, artist_name: str, spotify_id: str):
    key = normalize_key(key)
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            logging.debug(f'Track already exists for key {key}. Updating fields')
            track.track_name = track_name
            track.artist_name = artist_name
            track.spotify_id = spotify_id
        else:
            logging.info(f'Creating new track in database for {key}')
            track = Tracks(key=key, track_name=track_name, artist_name=artist_name, spotify_id=spotify_id)
            session.add(track)
        session.commit()

def get_track(key: str):
    key = normalize_key(key)
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            return {
                "key": track.key,
                "track_name": track.track_name,
                "artist_name": track.artist_name,
                "spotify_id": track.spotify_id,
            }
        logging.error(f'No track found for key {key}')
        return None

def get_track_id(key: str):
    key = normalize_key(key)
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            logging.debug(f'Track found in database: {track.spotify_id}')
            return track.spotify_id 
        else:
            logging.error(f'No track found for key {key}')
            return None

def get_track_name(key: str):
    key = normalize_key(key)
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            return track.track_name 
        else:
            logging.error(f'No track name found for key {key}')
            return None

def get_artist_name(key: str):
    key = normalize_key(key)
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            return track.artist_name 
        else:
            logging.error(f'No artist name found for key {key}')
            return None

def delete_track(key: str):
    key = normalize_key(key)
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            logging.info(f'Deleting track from database: {track.spotify_id}')
            session.delete(track)
            session.commit()
        else:
            logging.error(f'No track found for key {key}')
            return None

###################################################################################
#################### Functions for managing credits ###############################
###################################################################################

def set_credits(num: int):
    with Session(engine) as session:
        credit = session.query(Credits).first()
        if credit:
            logging.info(f'Setting credits to {num}')
            credit.credit_count = num
        else:
            logging.debug(f'Credit count unset. Setting to {num}')
            credit = Credits(credit_count=num)
            session.add(credit)
        session.commit()

def get_credits():
    with Session(engine) as session:
        credit = session.query(Credits).first()
        if credit:
            return credit.credit_count
        else:
            logging.info('Credit count unset. Initializing to 0')
            credit = Credits(credit_count=0)
            session.add(credit)
            session.commit()
            return credit.credit_count

def increment_credits():
    with Session(engine) as session:
        credit = session.query(Credits).first()
        if credit:
            logging.debug(f'Incrementing credits by 1')
            credit.credit_count += 1
        else:
            logging.info('Credit count unset. Initializing to 1')
            credit = Credits(credit_count=1)
            session.add(credit)
        session.commit()
        logging.info(f'Credit count {credit.credit_count}')

def decrement_credits():
    with Session(engine) as session:
        credit = session.query(Credits).first()
        if credit:
            logging.debug(f'Decrementing credits by 1')
            credit.credit_count -= 1
            session.commit()
            logging.info(f'Credit count {get_credits()}')
        else:
            logging.error(f'Credit count unset')
            return None

###################################################################################
#################### Functions for cabinet light settings ##########################
###################################################################################

def ensure_cabinet_lights_settings(r: int, g: int, b: int, on_time: str, off_time: str):
    with Session(engine) as session:
        settings = session.query(CabinetLightsSettings).filter(CabinetLightsSettings.id == 1).first()
        if not settings:
            settings = CabinetLightsSettings(
                id=1,
                current_r=r,
                current_g=g,
                current_b=b,
                saved_r=r,
                saved_g=g,
                saved_b=b,
                current_on_time=on_time,
                current_off_time=off_time,
                saved_on_time=on_time,
                saved_off_time=off_time,
            )
            session.add(settings)
            session.commit()

def get_cabinet_lights_settings():
    with Session(engine) as session:
        settings = session.query(CabinetLightsSettings).filter(CabinetLightsSettings.id == 1).first()
        if not settings:
            logging.error("Cabinet light settings unset")
            return None
        return {
            "r": settings.current_r,
            "g": settings.current_g,
            "b": settings.current_b,
            "on_time": settings.current_on_time,
            "off_time": settings.current_off_time,
        }
