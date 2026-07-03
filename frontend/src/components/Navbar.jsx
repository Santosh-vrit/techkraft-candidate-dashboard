import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Navbar() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="navbar">
      <Link to="/" className="brand">
        TechKraft Candidate Review
      </Link>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span className="badge">{role}</span>
        <button
          className="secondary"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Log out
        </button>
      </div>
    </div>
  );
}
