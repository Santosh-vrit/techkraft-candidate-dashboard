import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import Navbar from "../components/Navbar.jsx";
import { useAuth } from "../context/AuthContext.jsx";

const CATEGORIES = ["Technical Skills", "Communication", "Problem Solving", "Culture Fit", "Experience"];

export default function CandidateDetail() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();

  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [summaryError, setSummaryError] = useState("");
  const pollRef = useRef(null);

  const refreshCandidate = useCallback(async () => {
    setError("");
    try {
      const data = await api.getCandidate(id);
      setCandidate(data);
      return data;
    } catch (err) {
      setError(err.message || "Failed to load candidate");
      return null;
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refreshCandidate();
    return () => clearTimeout(pollRef.current);
  }, [refreshCandidate]);

  useEffect(() => {
    if (candidate?.ai_summary_status === "pending") {
      pollRef.current = setTimeout(async () => {
        try {
          await refreshCandidate();
        } catch {
          setSummaryError("Lost connection while waiting for the AI summary.");
        }
      }, 1200);
    }
    return () => clearTimeout(pollRef.current);
  }, [candidate, refreshCandidate]);

  async function handleTriggerSummary() {
    setSummaryError("");
    try {
      const response = await api.triggerSummary(id);
      setCandidate((currentCandidate) => ({
        ...currentCandidate,
        ai_summary_status: response.ai_summary_status,
        ai_summary: null,
      }));
    } catch (err) {
      setSummaryError(err.message || "Failed to trigger AI summary");
    }
  }

  async function handleDelete() {
    if (!confirm("Archive this candidate? This is a soft delete, not permanent removal.")) return;
    try {
      await api.deleteCandidate(id);
      navigate("/");
    } catch (err) {
      setError(err.message || "Failed to archive candidate");
    }
  }

  const canArchiveCandidate = isAdmin && candidate?.status !== "archived";

  if (loading) {
    return (
      <div>
        <Navbar />
        <div className="container">
          <span className="spinner" /> Loading candidate...
        </div>
      </div>
    );
  }

  if (error && !candidate) {
    return (
      <div>
        <Navbar />
        <div className="container">
          <div className="error-banner">{error}</div>
          <button className="secondary" onClick={() => navigate("/")}>
            Back to list
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Navbar />
      <div className="container">
        <button className="secondary" onClick={() => navigate("/")} style={{ marginBottom: 16 }}>
          Back to list
        </button>

        {error && <div className="error-banner">{error}</div>}

        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <h2 style={{ marginBottom: 4 }}>{candidate.name}</h2>
              <p className="muted" style={{ marginTop: 0 }}>
                {candidate.email} &middot; applied for <strong>{candidate.role_applied}</strong>
              </p>
            </div>
            <span className={`badge ${candidate.status}`}>{candidate.status}</span>
          </div>
          <div style={{ marginTop: 10 }}>
            {candidate.skills.map((skillName) => (
              <span className="skill-tag" key={skillName}>
                {skillName}
              </span>
            ))}
          </div>
          {canArchiveCandidate && (
            <button className="danger" style={{ marginTop: 14 }} onClick={handleDelete}>
              Archive candidate
            </button>
          )}
        </div>

        <AiSummaryPanel
          candidate={candidate}
          summaryError={summaryError}
          onTrigger={handleTriggerSummary}
        />

        <ScoresPanel candidate={candidate} onScored={refreshCandidate} />

        {isAdmin && <InternalNotesPanel candidate={candidate} onSaved={refreshCandidate} />}
      </div>
    </div>
  );
}

function AiSummaryPanel({ candidate, summaryError, onTrigger }) {
  const status = candidate.ai_summary_status;
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>AI Summary</h3>
        <button onClick={onTrigger} disabled={status === "pending"}>
          {status === "pending" ? "Generating..." : "Generate summary"}
        </button>
      </div>

      <div style={{ marginTop: 12 }}>
        {status === "pending" && (
          <p className="muted">
            <span className="spinner" /> Generating AI summary, this takes a couple of seconds...
          </p>
        )}
        {status === "failed" && (
          <div className="error-banner">The AI summary generation failed. Please try again.</div>
        )}
        {summaryError && <div className="error-banner">{summaryError}</div>}
        {status === "completed" && candidate.ai_summary && <p>{candidate.ai_summary}</p>}
        {status === "none" && !summaryError && (
          <p className="muted">No summary generated yet. Click "Generate summary" to create one.</p>
        )}
      </div>
    </div>
  );
}

function ScoresPanel({ candidate, onScored }) {
  const { isAdmin } = useAuth();
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [score, setScore] = useState(5);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.submitScore(candidate.id, { category, score: Number(score), note });
      setNote("");
      onScored();
    } catch (err) {
      setError(err.message || "Failed to submit score");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>{isAdmin ? "All reviewer scores" : "Your scores"}</h3>
      {candidate.scores.length === 0 ? (
        <p className="muted">No scores submitted yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Category</th>
              <th>Score</th>
              {isAdmin && <th>Reviewer</th>}
              <th>Note</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {candidate.scores.map((scoreEntry) => (
              <tr key={scoreEntry.id}>
                <td>{scoreEntry.category}</td>
                <td>{scoreEntry.score} / 5</td>
                {isAdmin && <td className="muted">{scoreEntry.reviewer_email}</td>}
                <td>{scoreEntry.note}</td>
                <td className="muted">{new Date(scoreEntry.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4>Submit a score</h4>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((categoryName) => (
              <option key={categoryName} value={categoryName}>
                {categoryName}
              </option>
            ))}
          </select>
          <select value={score} onChange={(e) => setScore(e.target.value)}>
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <input placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <button type="submit" disabled={saving}>
          {saving ? "Submitting..." : "Submit score"}
        </button>
      </form>
    </div>
  );
}

function InternalNotesPanel({ candidate, onSaved }) {
  const [notes, setNotes] = useState(candidate.internal_notes || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setNotes(candidate.internal_notes || "");
  }, [candidate.internal_notes]);

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await api.updateNotes(candidate.id, notes);
      onSaved();
    } catch (err) {
      setError(err.message || "Failed to save notes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Internal Notes (admin only)</h3>
      {error && <div className="error-banner">{error}</div>}
      <textarea
        rows={4}
        style={{ width: "100%" }}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Confidential notes visible only to admins"
      />
      <div style={{ marginTop: 10 }}>
        <button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save notes"}
        </button>
      </div>
    </div>
  );
}
