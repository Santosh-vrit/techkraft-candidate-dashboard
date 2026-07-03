import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function Login() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data =
        mode === "login" ? await api.login(email, password) : await api.register(email, password, name);
      login(data.access_token, data.role);
      navigate("/");
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="card login-card">
        <h2 style={{ marginTop: 0 }}>{mode === "login" ? "Sign in" : "Create reviewer account"}</h2>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <div className="form-row">
              <input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
          )}
          <div className="form-row">
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
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={mode === "register" ? 8 : undefined}
              required
            />
          </div>
          <button type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Register"}
          </button>
        </form>
        <p className="muted" style={{ marginTop: 14 }}>
          {mode === "login" ? (
            <>
              New reviewer?{" "}
              <a href="#" onClick={() => setMode("register")}>
                Create an account
              </a>{" "}
              (registrations are always created with the reviewer role).
            </>
          ) : (
            <>
              Already have an account?{" "}
              <a href="#" onClick={() => setMode("login")}>
                Sign in
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
