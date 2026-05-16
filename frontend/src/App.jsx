import { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./App.css";

const API_BASE = "/api";
const emptyForm = {
  key: "",
  track_name: "",
  artist_name: "",
  spotify_id: "",
};
const defaultLightSettings = {
  r: 255,
  g: 90,
  b: 0,
  on_time: "07:00",
  off_time: "22:00",
  saved_r: 255,
  saved_g: 90,
  saved_b: 0,
  saved_on_time: "07:00",
  saved_off_time: "22:00",
  has_unsaved_changes: false,
};
const CREDITS_REFRESH_MS = 2000;
const SONOS_PLAYLIST_REFRESH_MS = 5000;

function rgbToHex({ r, g, b }) {
  return `#${[r, g, b].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  return {
    r: parseInt(value.slice(0, 2), 16),
    g: parseInt(value.slice(2, 4), 16),
    b: parseInt(value.slice(4, 6), 16),
  };
}

function sortTracks(tracks) {
  return [...tracks].sort((a, b) => a.key.localeCompare(b.key, undefined, { numeric: true, sensitivity: "base" }));
}

function normalizeQueueItems(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

function sonosUrl(apiUrl, zone, ...parts) {
  const base = apiUrl.replace(/\/$/, "");
  const path = [zone, ...parts].map((part) => encodeURIComponent(part)).join("/");
  return `${base}/${path}`;
}

function App() {
  const [tracks, setTracks] = useState([]);
  const [selectedKey, setSelectedKey] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [lights, setLights] = useState(defaultLightSettings);
  const [lightsBusy, setLightsBusy] = useState(false);
  const [lightsError, setLightsError] = useState("");
  const [credits, setCredits] = useState(null);
  const [creditsBusy, setCreditsBusy] = useState(false);
  const [sonosConfig, setSonosConfig] = useState(null);
  const [playlist, setPlaylist] = useState([]);
  const [playlistLoading, setPlaylistLoading] = useState(true);
  const [playlistError, setPlaylistError] = useState("");
  const [volume, setVolume] = useState(null);
  const [volumeLoading, setVolumeLoading] = useState(true);
  const [volumeBusy, setVolumeBusy] = useState(false);
  const [volumeError, setVolumeError] = useState("");
  const [sonosBusy, setSonosBusy] = useState(false);
  const lightsPreviewRequest = useRef(0);

  const selectedTrack = useMemo(
    () => tracks.find((track) => track.key === selectedKey),
    [tracks, selectedKey],
  );

  const filteredTracks = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) return tracks;
    return tracks.filter((track) =>
      [track.key, track.track_name, track.artist_name, track.spotify_id]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [tracks, filter]);

  async function loadTracks() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/tracks`);
      if (!response.ok) throw new Error("Could not load tracks");
      const data = await response.json();
      setTracks(sortTracks(data));
      if (selectedKey && !data.some((track) => track.key === selectedKey)) {
        resetForm();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadCabinetLights() {
    setLightsError("");
    try {
      const response = await fetch(`${API_BASE}/cabinet-lights`);
      if (!response.ok) throw new Error("Could not load cabinet light settings");
      setLights(await response.json());
    } catch (err) {
      setLightsError(err.message);
    }
  }

  async function loadCredits() {
    try {
      const response = await fetch(`${API_BASE}/credits`);
      if (!response.ok) throw new Error("Could not load credits");
      const data = await response.json();
      setCredits(data.credit_count);
    } catch (err) {
      setCredits(null);
    }
  }

  async function loadSonosConfig() {
    const response = await fetch(`${API_BASE}/sonos-config`);
    if (!response.ok) throw new Error("Could not load Sonos settings");
    return response.json();
  }

  async function loadSonosPlaylist(config = sonosConfig) {
    if (!config?.api_url || !config?.zone) return;

    setPlaylistError("");
    try {
      const response = await fetch(sonosUrl(config.api_url, config.zone, "queue", "detailed"));
      if (!response.ok) throw new Error("Could not load Sonos playlist");
      const data = await response.json();
      setPlaylist(normalizeQueueItems(data));
    } catch (err) {
      setPlaylistError(err.message);
    } finally {
      setPlaylistLoading(false);
    }
  }

  async function loadSonosVolume(config = sonosConfig) {
    if (!config?.api_url || !config?.zone) return;

    setVolumeError("");
    try {
      const response = await fetch(sonosUrl(config.api_url, config.zone, "state"));
      if (!response.ok) throw new Error("Could not load Sonos volume");
      const data = await response.json();
      setVolume(Number(data.volume));
    } catch (err) {
      setVolumeError(err.message);
    } finally {
      setVolumeLoading(false);
    }
  }

  async function refreshSonos(config = sonosConfig) {
    await Promise.all([loadSonosPlaylist(config), loadSonosVolume(config)]);
  }

  async function runSonosAction(...parts) {
    if (!sonosConfig?.api_url || !sonosConfig?.zone) return null;

    setSonosBusy(true);
    setPlaylistError("");
    setVolumeError("");
    try {
      const response = await fetch(sonosUrl(sonosConfig.api_url, sonosConfig.zone, ...parts));
      if (!response.ok) throw new Error("Could not update Sonos playback");
      await refreshSonos(sonosConfig);
      return response;
    } catch (err) {
      setPlaylistError(err.message);
      return null;
    } finally {
      setSonosBusy(false);
    }
  }

  async function clearSonosPlaylist() {
    await runSonosAction("clearqueue");
  }

  async function setSonosVolume(nextVolume) {
    if (!sonosConfig?.api_url || !sonosConfig?.zone) return;

    const clampedVolume = Math.max(0, Math.min(100, Number(nextVolume)));
    setVolume(clampedVolume);
    setVolumeBusy(true);
    setVolumeError("");
    try {
      const response = await fetch(sonosUrl(sonosConfig.api_url, sonosConfig.zone, "volume", String(clampedVolume)));
      if (!response.ok) throw new Error("Could not update Sonos volume");
      await loadSonosVolume(sonosConfig);
    } catch (err) {
      setVolumeError(err.message);
    } finally {
      setVolumeBusy(false);
    }
  }

  async function initialiseSonosPlaylist() {
    setPlaylistLoading(true);
    setVolumeLoading(true);
    setPlaylistError("");
    setVolumeError("");
    try {
      const config = await loadSonosConfig();
      setSonosConfig(config);
      await refreshSonos(config);
    } catch (err) {
      setPlaylistError(err.message);
      setPlaylistLoading(false);
      setVolumeLoading(false);
    }
  }

  async function changeCredits(direction) {
    setCreditsBusy(true);
    try {
      const response = await fetch(`${API_BASE}/credits/${direction}`, { method: "POST" });
      if (!response.ok) throw new Error("Could not update credits");
      const data = await response.json();
      setCredits(data.credit_count);
    } catch (err) {
      setCredits(null);
    } finally {
      setCreditsBusy(false);
    }
  }

  useEffect(() => {
    loadTracks();
    loadCabinetLights();
    loadCredits();
    initialiseSonosPlaylist();
  }, []);

  useEffect(() => {
    const interval = window.setInterval(loadCredits, CREDITS_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!sonosConfig) return undefined;
    const interval = window.setInterval(() => refreshSonos(sonosConfig), SONOS_PLAYLIST_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [sonosConfig]);

  useEffect(() => {
    function revertUnsavedLights() {
      if (!lights.has_unsaved_changes) return;
      if (navigator.sendBeacon) {
        navigator.sendBeacon(`${API_BASE}/cabinet-lights/revert`, new Blob([], { type: "application/json" }));
        return;
      }
      fetch(`${API_BASE}/cabinet-lights/revert`, { method: "POST", keepalive: true });
    }

    window.addEventListener("pagehide", revertUnsavedLights);
    return () => window.removeEventListener("pagehide", revertUnsavedLights);
  }, [lights.has_unsaved_changes]);

  function resetForm() {
    setSelectedKey(null);
    setForm(emptyForm);
    setError("");
  }

  function selectTrack(track) {
    setSelectedKey(track.key);
    setForm({
      key: track.key,
      track_name: track.track_name || "",
      artist_name: track.artist_name || "",
      spotify_id: track.spotify_id || "",
    });
    setError("");
  }

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function saveTrack(event) {
    event.preventDefault();
    setSaving(true);
    setError("");

    const trimmed = {
      key: form.key.trim(),
      track_name: form.track_name.trim(),
      artist_name: form.artist_name.trim(),
      spotify_id: form.spotify_id.trim(),
    };

    if (!trimmed.key || !trimmed.spotify_id) {
      setSaving(false);
      setError("Key and Spotify ID are required.");
      return;
    }

    try {
      const isEditing = Boolean(selectedTrack);
      const response = await fetch(
        isEditing ? `${API_BASE}/tracks/${encodeURIComponent(selectedKey)}` : `${API_BASE}/tracks`,
        {
          method: isEditing ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            isEditing
              ? {
                  track_name: trimmed.track_name,
                  artist_name: trimmed.artist_name,
                  spotify_id: trimmed.spotify_id,
                }
              : trimmed,
          ),
        },
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Could not save track");
      }

      const saved = await response.json();
      setTracks((current) => {
        const exists = current.some((track) => track.key === saved.key);
        if (exists) {
          return sortTracks(current.map((track) => (track.key === saved.key ? saved : track)));
        }
        return sortTracks([...current, saved]);
      });
      setSelectedKey(saved.key);
      setForm(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteTrack() {
    if (!selectedKey) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/tracks/${encodeURIComponent(selectedKey)}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Could not delete track");
      setTracks((current) => current.filter((track) => track.key !== selectedKey));
      resetForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function previewCabinetLights(nextSettings) {
    const requestId = ++lightsPreviewRequest.current;
    setLightsError("");
    try {
      const response = await fetch(`${API_BASE}/cabinet-lights/preview`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextSettings),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Could not preview cabinet light settings");
      }
      const nextLights = await response.json();
      if (requestId === lightsPreviewRequest.current) {
        setLights(nextLights);
      }
    } catch (err) {
      setLightsError(err.message);
    }
  }

  function updateCabinetColor(event) {
    const rgb = hexToRgb(event.target.value);
    setLights((current) => ({ ...current, ...rgb, has_unsaved_changes: true }));
    previewCabinetLights(rgb);
  }

  function updateCabinetTime(event) {
    const { name, value } = event.target;
    setLights((current) => ({ ...current, [name]: value, has_unsaved_changes: true }));
    previewCabinetLights({ [name]: value });
  }

  async function saveCabinetLights() {
    lightsPreviewRequest.current += 1;
    setLightsBusy(true);
    setLightsError("");
    try {
      const response = await fetch(`${API_BASE}/cabinet-lights/save`, { method: "POST" });
      if (!response.ok) throw new Error("Could not save cabinet light settings");
      setLights(await response.json());
    } catch (err) {
      setLightsError(err.message);
    } finally {
      setLightsBusy(false);
    }
  }

  async function revertCabinetLights() {
    lightsPreviewRequest.current += 1;
    setLightsBusy(true);
    setLightsError("");
    try {
      const response = await fetch(`${API_BASE}/cabinet-lights/revert`, { method: "POST" });
      if (!response.ok) throw new Error("Could not revert cabinet light settings");
      setLights(await response.json());
    } catch (err) {
      setLightsError(err.message);
    } finally {
      setLightsBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="track-list" aria-label="Tracks">
          <div className="list-header">
            <div>
              <h1>DimePi Tracks</h1>
              <p>{tracks.length} saved selections</p>
            </div>
            <div className="credits-box" aria-label="Machine credits">
              <span>Credits: {credits === null ? "..." : credits}</span>
              <div className="credits-actions">
                <button
                  type="button"
                  className="credit-button"
                  onClick={() => changeCredits("decrement")}
                  disabled={creditsBusy || credits === 0}
                  aria-label="Decrement credits"
                >
                  -
                </button>
                <button
                  type="button"
                  className="credit-button"
                  onClick={() => changeCredits("increment")}
                  disabled={creditsBusy}
                  aria-label="Increment credits"
                >
                  +
                </button>
              </div>
            </div>
          </div>

          <label className="search">
            <span>Search</span>
            <input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Key, title, artist, Spotify ID" />
          </label>

          <div className="rows">
            {loading ? <div className="empty-state">Loading tracks...</div> : null}
            {!loading && filteredTracks.length === 0 ? <div className="empty-state">No tracks found.</div> : null}
            {filteredTracks.map((track) => (
              <button
                type="button"
                className={track.key === selectedKey ? "track-row selected" : "track-row"}
                key={track.key}
                onClick={() => selectTrack(track)}
              >
                <span className="key-badge">{track.key}</span>
                <span className="track-meta">
                  <strong>{track.track_name || "Untitled track"}</strong>
                  <small>{track.artist_name || "Unknown artist"}</small>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="editor" aria-label="Track editor">
          <div className="editor-header">
            <div>
              <p className="eyebrow">{selectedTrack ? "Editing selection" : "New selection"}</p>
              <h2>{selectedTrack ? selectedTrack.key : "Add a track"}</h2>
            </div>
            <button type="button" className="secondary" onClick={resetForm}>
              New
            </button>
          </div>

          {error ? <div className="error">{error}</div> : null}

          <form className="track-form" onSubmit={saveTrack}>
            <label>
              <span>Keypad code</span>
              <input name="key" value={form.key} onChange={updateField} disabled={Boolean(selectedTrack)} required />
            </label>

            <label>
              <span>Track name</span>
              <input name="track_name" value={form.track_name} onChange={updateField} />
            </label>

            <label>
              <span>Artist</span>
              <input name="artist_name" value={form.artist_name} onChange={updateField} />
            </label>

            <label>
              <span>Spotify ID or URI</span>
              <input name="spotify_id" value={form.spotify_id} onChange={updateField} required />
            </label>

            <div className="actions">
              <button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save track"}
              </button>
              <button type="button" className="danger" onClick={deleteTrack} disabled={!selectedTrack || saving}>
                Delete
              </button>
            </div>
          </form>

          <section className="sonos-panel" aria-label="Sonos playlist">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Sonos playlist</p>
                <h3>{sonosConfig?.zone || "Loading zone..."}</h3>
              </div>
            </div>

            {playlistError ? <div className="error inline-error">{playlistError}</div> : null}
            {volumeError ? <div className="error inline-error">{volumeError}</div> : null}

            <div className="volume-control">
              <label>
                <span>Volume</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={volume ?? 0}
                  onChange={(event) => setVolume(Number(event.target.value))}
                  onPointerUp={(event) => setSonosVolume(event.currentTarget.value)}
                  onKeyUp={(event) => {
                    if (["ArrowLeft", "ArrowRight", "Home", "End", "Enter"].includes(event.key)) {
                      setSonosVolume(event.currentTarget.value);
                    }
                  }}
                  disabled={volumeLoading || volumeBusy || !sonosConfig}
                />
              </label>
              <div className="volume-readout">{volumeLoading || volume === null ? "..." : `${volume}%`}</div>
              <div className="volume-buttons">
                <button type="button" className="secondary compact" onClick={() => setSonosVolume((volume ?? 0) - 5)} disabled={volumeBusy || volumeLoading || !sonosConfig}>
                  -
                </button>
                <button type="button" className="secondary compact" onClick={() => setSonosVolume((volume ?? 0) + 5)} disabled={volumeBusy || volumeLoading || !sonosConfig}>
                  +
                </button>
              </div>
            </div>

            <div className="transport-controls" aria-label="Sonos playback controls">
              <button type="button" className="secondary compact" onClick={() => runSonosAction("previous")} disabled={sonosBusy || !sonosConfig}>
                Previous
              </button>
              <button type="button" className="secondary compact" onClick={() => runSonosAction("timeseek", "0")} disabled={sonosBusy || !sonosConfig}>
                Restart
              </button>
              <button type="button" className="secondary compact" onClick={() => runSonosAction("play")} disabled={sonosBusy || !sonosConfig}>
                Play
              </button>
              <button type="button" className="secondary compact" onClick={() => runSonosAction("pause")} disabled={sonosBusy || !sonosConfig}>
                Pause
              </button>
              <button type="button" className="secondary compact" onClick={() => runSonosAction("pause")} disabled={sonosBusy || !sonosConfig}>
                Stop
              </button>
              <button type="button" className="secondary compact" onClick={() => runSonosAction("next")} disabled={sonosBusy || !sonosConfig}>
                Next
              </button>
              <button type="button" className="danger compact" onClick={clearSonosPlaylist} disabled={sonosBusy || !sonosConfig || playlist.length === 0}>
                Clear
              </button>
            </div>

            {playlistLoading ? <div className="empty-state inline-empty">Loading playlist...</div> : null}
            {!playlistLoading && !playlistError && playlist.length === 0 ? (
              <div className="empty-state inline-empty">The Sonos playlist is empty.</div>
            ) : null}

            {playlist.length > 0 ? (
              <ol className="playlist-rows">
                {playlist.map((item, index) => (
                  <li className="playlist-row" key={`${item.uri || item.title || "track"}-${index}`}>
                    <span className="playlist-index">{index + 1}</span>
                    <span className="track-meta">
                      <strong>{item.title || "Untitled track"}</strong>
                      <small>{[item.artist, item.album].filter(Boolean).join(" - ") || "Unknown artist"}</small>
                    </span>
                  </li>
                ))}
              </ol>
            ) : null}
          </section>

          <section className="lights-panel" aria-label="Cabinet light settings">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Cabinet lights</p>
                <h3>Colour and schedule</h3>
              </div>
              <span className={lights.has_unsaved_changes ? "status unsaved" : "status"}>{lights.has_unsaved_changes ? "Unsaved" : "Saved"}</span>
            </div>

            {lightsError ? <div className="error inline-error">{lightsError}</div> : null}

            <div className="lights-grid">
              <label className="colour-picker">
                <span>Colour</span>
                <input type="color" value={rgbToHex(lights)} onChange={updateCabinetColor} />
              </label>
              <div className="colour-readout" style={{ background: rgbToHex(lights) }}>
                <span>
                  RGB {lights.r}, {lights.g}, {lights.b}
                </span>
              </div>
              <label>
                <span>On time</span>
                <input type="time" name="on_time" value={lights.on_time} onChange={updateCabinetTime} />
              </label>
              <label>
                <span>Off time</span>
                <input type="time" name="off_time" value={lights.off_time} onChange={updateCabinetTime} />
              </label>
            </div>

            <div className="actions">
              <button type="button" onClick={saveCabinetLights} disabled={lightsBusy || !lights.has_unsaved_changes}>
                {lightsBusy ? "Saving..." : "Save lights"}
              </button>
              <button type="button" className="secondary" onClick={revertCabinetLights} disabled={lightsBusy || !lights.has_unsaved_changes}>
                Revert
              </button>
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
