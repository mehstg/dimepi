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
      setTracks(data);
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

  useEffect(() => {
    loadTracks();
    loadCabinetLights();
  }, []);

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
          return current.map((track) => (track.key === saved.key ? saved : track));
        }
        return [...current, saved].sort((a, b) => a.key.localeCompare(b.key, undefined, { numeric: true }));
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
            <button type="button" className="secondary compact" onClick={loadTracks} disabled={loading}>
              Refresh
            </button>
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
