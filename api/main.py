import os
import re
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class TrackIn(BaseModel):
    key: str = Field(min_length=1, max_length=16)
    track_name: Optional[str] = ""
    artist_name: Optional[str] = ""
    spotify_id: str = Field(min_length=1)


class TrackUpdate(BaseModel):
    track_name: Optional[str] = ""
    artist_name: Optional[str] = ""
    spotify_id: str = Field(min_length=1)


class Track(TrackIn):
    pass


class CabinetLightsPatch(BaseModel):
    r: Optional[int] = Field(default=None, ge=0, le=255)
    g: Optional[int] = Field(default=None, ge=0, le=255)
    b: Optional[int] = Field(default=None, ge=0, le=255)
    on_time: Optional[str] = None
    off_time: Optional[str] = None


class CabinetLightsSettings(BaseModel):
    r: int
    g: int
    b: int
    on_time: str
    off_time: str
    saved_r: int
    saved_g: int
    saved_b: int
    saved_on_time: str
    saved_off_time: str
    has_unsaved_changes: bool


class Credits(BaseModel):
    credit_count: int


class SonosConfig(BaseModel):
    api_url: str
    zone: str


app = FastAPI(title="DimePi Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def normalize_key(key: str):
    return key.strip().upper()


def parse_lights_color(value: str):
    try:
        rgb = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise RuntimeError("general.cabinet_lights_colour must be R,G,B") from exc
    if len(rgb) != 3 or any(component < 0 or component > 255 for component in rgb):
        raise RuntimeError("general.cabinet_lights_colour must contain three values from 0 to 255")
    return rgb


def parse_lights_time(value: str, field_name: str):
    if not TIME_PATTERN.match(value):
        raise RuntimeError(f"general.{field_name} must use HH:MM in 24-hour time")
    return value


DATABASE_PATH = os.environ.get("DIMEPI_DATABASE_PATH", "/var/lib/dimepi/database.db")
DEFAULT_LIGHTS_COLOR = parse_lights_color(
    os.environ.get("DIMEPI_CABINET_LIGHTS_COLOUR", "255,90,0")
)
DEFAULT_LIGHTS_ON_TIME = parse_lights_time(
    os.environ.get("DIMEPI_CABINET_LIGHTS_ON_TIME", "07:00"),
    "cabinet_lights_on_time",
)
DEFAULT_LIGHTS_OFF_TIME = parse_lights_time(
    os.environ.get("DIMEPI_CABINET_LIGHTS_OFF_TIME", "22:00"),
    "cabinet_lights_off_time",
)


def init_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                key TEXT PRIMARY KEY,
                track_name TEXT,
                artist_name TEXT,
                spotify_id TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS credits (
                id INTEGER PRIMARY KEY,
                credit_count INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cabinet_lights_settings (
                id INTEGER PRIMARY KEY,
                current_r INTEGER NOT NULL,
                current_g INTEGER NOT NULL,
                current_b INTEGER NOT NULL,
                saved_r INTEGER NOT NULL,
                saved_g INTEGER NOT NULL,
                saved_b INTEGER NOT NULL,
                current_on_time TEXT NOT NULL,
                current_off_time TEXT NOT NULL,
                saved_on_time TEXT NOT NULL,
                saved_off_time TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO cabinet_lights_settings (
                id,
                current_r,
                current_g,
                current_b,
                saved_r,
                saved_g,
                saved_b,
                current_on_time,
                current_off_time,
                saved_on_time,
                saved_off_time
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_LIGHTS_COLOR[0],
                DEFAULT_LIGHTS_COLOR[1],
                DEFAULT_LIGHTS_COLOR[2],
                DEFAULT_LIGHTS_COLOR[0],
                DEFAULT_LIGHTS_COLOR[1],
                DEFAULT_LIGHTS_COLOR[2],
                DEFAULT_LIGHTS_ON_TIME,
                DEFAULT_LIGHTS_OFF_TIME,
                DEFAULT_LIGHTS_ON_TIME,
                DEFAULT_LIGHTS_OFF_TIME,
            ),
        )


def get_credit_count():
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT credit_count
            FROM credits
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
        if row is not None:
            return row["credit_count"]

        connection.execute(
            """
            INSERT INTO credits (credit_count)
            VALUES (0)
            """
        )
        return 0


def update_credit_count(delta: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, credit_count
            FROM credits
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            credit_count = max(0, delta)
            connection.execute(
                """
                INSERT INTO credits (credit_count)
                VALUES (?)
                """,
                (credit_count,),
            )
            return credit_count

        credit_count = max(0, row["credit_count"] + delta)
        connection.execute(
            """
            UPDATE credits
            SET credit_count = ?
            WHERE id = ?
            """,
            (credit_count, row["id"]),
        )
        return credit_count


def validate_time(value: Optional[str], field_name: str):
    if value is not None and not TIME_PATTERN.match(value):
        raise HTTPException(status_code=422, detail=f"{field_name} must use HH:MM in 24-hour time")


def cabinet_lights_response(row):
    return {
        "r": row["current_r"],
        "g": row["current_g"],
        "b": row["current_b"],
        "on_time": row["current_on_time"],
        "off_time": row["current_off_time"],
        "saved_r": row["saved_r"],
        "saved_g": row["saved_g"],
        "saved_b": row["saved_b"],
        "saved_on_time": row["saved_on_time"],
        "saved_off_time": row["saved_off_time"],
        "has_unsaved_changes": (
            row["current_r"],
            row["current_g"],
            row["current_b"],
            row["current_on_time"],
            row["current_off_time"],
        ) != (
            row["saved_r"],
            row["saved_g"],
            row["saved_b"],
            row["saved_on_time"],
            row["saved_off_time"],
        ),
    }


@app.on_event("startup")
def startup():
    init_database()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/credits", response_model=Credits)
def get_credits():
    return {"credit_count": get_credit_count()}


@app.get("/sonos-config", response_model=SonosConfig)
def get_sonos_config():
    api_url = os.environ.get("SONOS_API_URL", "http://localhost:5005")
    zone = os.environ.get("SONOS_ZONE", "Cabin")
    api_url = api_url.rstrip("/")
    if not api_url or not zone:
        raise HTTPException(status_code=500, detail="Missing Sonos API URL or zone config")
    return {
        "api_url": api_url,
        "zone": zone,
    }


@app.post("/credits/increment", response_model=Credits)
def increment_credits():
    return {"credit_count": update_credit_count(1)}


@app.post("/credits/decrement", response_model=Credits)
def decrement_credits():
    return {"credit_count": update_credit_count(-1)}


@app.get("/cabinet-lights", response_model=CabinetLightsSettings)
def get_cabinet_lights():
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT current_r, current_g, current_b, saved_r, saved_g, saved_b,
                   current_on_time, current_off_time, saved_on_time, saved_off_time
            FROM cabinet_lights_settings
            WHERE id = 1
            """
        ).fetchone()
        if row is None:
            init_database()
            return get_cabinet_lights()
        return cabinet_lights_response(row)


@app.patch("/cabinet-lights/preview", response_model=CabinetLightsSettings)
def preview_cabinet_lights(settings: CabinetLightsPatch):
    validate_time(settings.on_time, "on_time")
    validate_time(settings.off_time, "off_time")
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cabinet_lights_settings
            SET current_r = COALESCE(?, current_r),
                current_g = COALESCE(?, current_g),
                current_b = COALESCE(?, current_b),
                current_on_time = COALESCE(?, current_on_time),
                current_off_time = COALESCE(?, current_off_time)
            WHERE id = 1
            """,
            (settings.r, settings.g, settings.b, settings.on_time, settings.off_time),
        )
    return get_cabinet_lights()


@app.post("/cabinet-lights/save", response_model=CabinetLightsSettings)
def save_cabinet_lights():
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cabinet_lights_settings
            SET saved_r = current_r,
                saved_g = current_g,
                saved_b = current_b,
                saved_on_time = current_on_time,
                saved_off_time = current_off_time
            WHERE id = 1
            """
        )
    return get_cabinet_lights()


@app.post("/cabinet-lights/revert", response_model=CabinetLightsSettings)
def revert_cabinet_lights():
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cabinet_lights_settings
            SET current_r = saved_r,
                current_g = saved_g,
                current_b = saved_b,
                current_on_time = saved_on_time,
                current_off_time = saved_off_time
            WHERE id = 1
            """
        )
    return get_cabinet_lights()


@app.get("/tracks", response_model=list[Track])
def list_tracks():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT key, track_name, artist_name, spotify_id
            FROM tracks
            ORDER BY key
            """
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/tracks", response_model=Track, status_code=status.HTTP_201_CREATED)
def create_track(track: TrackIn):
    key = normalize_key(track.key)
    spotify_id = track.spotify_id.strip()
    if not key or not spotify_id:
        raise HTTPException(status_code=422, detail="Key and Spotify ID are required")

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO tracks (key, track_name, artist_name, spotify_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    key,
                    track.track_name.strip() if track.track_name else "",
                    track.artist_name.strip() if track.artist_name else "",
                    spotify_id,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Track key already exists") from exc
    return get_track(key)


@app.get("/tracks/{key}", response_model=Track)
def get_track(key: str):
    key = normalize_key(key)
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT key, track_name, artist_name, spotify_id
            FROM tracks
            WHERE key = ?
            """,
            (key,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Track not found")
        return dict(row)


@app.put("/tracks/{key}", response_model=Track)
def update_track(key: str, track: TrackUpdate):
    key = normalize_key(key)
    spotify_id = track.spotify_id.strip()
    if not spotify_id:
        raise HTTPException(status_code=422, detail="Spotify ID is required")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tracks
            SET track_name = ?, artist_name = ?, spotify_id = ?
            WHERE key = ?
            """,
            (
                track.track_name.strip() if track.track_name else "",
                track.artist_name.strip() if track.artist_name else "",
                spotify_id,
                key,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Track not found")
    return get_track(key)


@app.delete("/tracks/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_track(key: str):
    key = normalize_key(key)
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM tracks WHERE key = ?", (key,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Track not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
