import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import Navbar from "../components/Navbar.jsx";
import { useAuth } from "../context/AuthContext.jsx";

const STATUSES = ["new", "reviewed", "hired", "rejected", "archived"];
const PAGE_SIZE = 20;
const pageHeaderStyle = { display: "flex", justifyContent: "space-between", alignItems: "center" };

export default function CandidateList() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("");
  const [roleApplied, setRoleApplied] = useState("");
  const [skill, setSkill] = useState("");
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const { isAdmin } = useAuth();
  const navigate = useNavigate();

  const refreshCandidates = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.listCandidates({
        status: status || undefined,
        role_applied: roleApplied || undefined,
        skill: skill || undefined,
        keyword: keyword || undefined,
        offset,
        limit: PAGE_SIZE,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message || "Failed to load candidates");
    } finally {
      setLoading(false);
    }
  }, [keyword, offset, roleApplied, skill, status]);

  useEffect(() => {
    refreshCandidates();
  }, [refreshCandidates]);

  function handleFilterSubmit(e) {
    e.preventDefault();
    setOffset(0);
    refreshCandidates();
  }

  const pageNumber = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <Navbar />
      <div className="container">
        <div style={pageHeaderStyle}>
          <h2>Candidates</h2>
          {isAdmin && (
            <button onClick={() => setShowCreate((value) => !value)}>
              {showCreate ? "Cancel" : "+ New Candidate"}
            </button>
          )}
        </div>

        {showCreate && (
          <CreateCandidateForm
            onCreated={() => {
              setShowCreate(false);
              refreshCandidates();
            }}
          />
        )}

        <form className="filters" onSubmit={handleFilterSubmit}>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>
          <input
            placeholder="Role applied"
            value={roleApplied}
            onChange={(e) => setRoleApplied(e.target.value)}
          />
          <input placeholder="Skill" value={skill} onChange={(e) => setSkill(e.target.value)} />
          <input
            placeholder="Search name or email"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
          <button type="submit">Filter</button>
        </form>

        {error && <div className="error-banner">{error}</div>}

        <div className="card">
          {loading ? (
            <p className="muted">
              <span className="spinner" /> Loading candidates...
            </p>
          ) : items.length === 0 ? (
            <p className="muted">No candidates match these filters.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role applied</th>
                  <th>Status</th>
                  <th>Skills</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((candidate) => (
                  <tr key={candidate.id} className="clickable" onClick={() => navigate(`/candidates/${candidate.id}`)}>
                    <td>{candidate.name}</td>
                    <td>{candidate.role_applied}</td>
                    <td>
                      <span className={`badge ${candidate.status}`}>{candidate.status}</span>
                    </td>
                    <td>
                      {candidate.skills.map((skillName) => (
                        <span className="skill-tag" key={skillName}>
                          {skillName}
                        </span>
                      ))}
                    </td>
                    <td className="muted">{new Date(candidate.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="pagination">
            <button
              className="secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </button>
            <span className="muted">
              Page {pageNumber} of {totalPages} ({total} total)
            </span>
            <button
              className="secondary"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CreateCandidateForm({ onCreated }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [roleApplied, setRoleApplied] = useState("");
  const [skills, setSkills] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createCandidate({
        name,
        email,
        role_applied: roleApplied,
        skills: skills
          .split(",")
          .map((skillName) => skillName.trim())
          .filter(Boolean),
      });
      onCreated();
    } catch (err) {
      setError(err.message || "Failed to create candidate");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      {error && <div className="error-banner">{error}</div>}
      <div className="form-row">
        <input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="form-row">
        <input
          placeholder="Role applied"
          value={roleApplied}
          onChange={(e) => setRoleApplied(e.target.value)}
          required
        />
        <input
          placeholder="Skills (comma separated)"
          value={skills}
          onChange={(e) => setSkills(e.target.value)}
        />
      </div>
      <button type="submit" disabled={saving}>
        {saving ? "Creating..." : "Create candidate"}
      </button>
    </form>
  );
}
