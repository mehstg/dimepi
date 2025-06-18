import os
import logging
import configparser
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session

config = configparser.ConfigParser()
config.read('config.ini')

database_path = config['database']['db_path']

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

engine = create_engine(f"sqlite:///{database_path}")

# Create tables only if database file doesn't exist yet
if not db_exists:
    logging.info(f"Database file {database_path} not found. Creating new database and tables.")
    SQLModel.metadata.create_all(engine)
else:
    logging.info(f"Database file {database_path} found. Using existing database.")

###################################################################################
#################### Functions for managing tracks ################################
###################################################################################

def set_track(key: str, track_name: str, artist_name: str, spotify_id: str):
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

def get_track_id(key: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            logging.debug(f'Track found in database: {track.spotify_id}')
            return track.spotify_id 
        else:
            logging.error(f'No track found for key {key}')
            return None

def get_track_name(key: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            return track.track_name 
        else:
            logging.error(f'No track name found for key {key}')
            return None

def get_artist_name(key: str):
    with Session(engine) as session:
        track = session.query(Tracks).filter(Tracks.key == key).first()
        if track:
            return track.artist_name 
        else:
            logging.error(f'No artist name found for key {key}')
            return None

def delete_track(key: str):
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
            logging.error(f'Credit count unset')
            return None

def increment_credits():
    with Session(engine) as session:
        credit = session.query(Credits).first()
        if credit:
            logging.debug(f'Incrementing credits by 1')
            credit.credit_count += 1
            session.commit()
            logging.info(f'Credit count {get_credits()}')
        else:
            logging.error(f'Credit count unset')
            return None

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
