import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

function decodeRole(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [role, setRole] = useState(() => localStorage.getItem("role"));

  const login = (accessToken, userRole) => {
    localStorage.setItem("token", accessToken);
    localStorage.setItem("role", userRole || decodeRole(accessToken));
    setToken(accessToken);
    setRole(userRole || decodeRole(accessToken));
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    setToken(null);
    setRole(null);
  };

  const value = useMemo(
    () => ({ token, role, isAdmin: role === "admin", isAuthenticated: !!token, login, logout }),
    [token, role]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
