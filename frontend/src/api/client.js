const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getToken() {
  return localStorage.getItem("token");
}

async function request(path, { method = "GET", body, params } = {}) {
  const url = new URL(API_URL + path);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {}
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  register: (email, password, name) =>
    request("/auth/register", { method: "POST", body: { email, password, name } }),
  login: (email, password) => request("/auth/login", { method: "POST", body: { email, password } }),

  listCandidates: (params) => request("/candidates", { params }),
  createCandidate: (payload) => request("/candidates", { method: "POST", body: payload }),
  getCandidate: (id) => request(`/candidates/${id}`),
  deleteCandidate: (id) => request(`/candidates/${id}`, { method: "DELETE" }),
  updateNotes: (id, internal_notes) =>
    request(`/candidates/${id}/notes`, { method: "PATCH", body: { internal_notes } }),
  submitScore: (id, payload) => request(`/candidates/${id}/scores`, { method: "POST", body: payload }),
  triggerSummary: (id) => request(`/candidates/${id}/summary`, { method: "POST" }),
};

export { API_URL, getToken };
