import { Navigate, Route, Routes } from "react-router-dom";
import CandidateDetail from "./pages/CandidateDetail.jsx";
import CandidateList from "./pages/CandidateList.jsx";
import Login from "./pages/Login.jsx";
import { useAuth } from "./context/AuthContext.jsx";

function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <CandidateList />
          </RequireAuth>
        }
      />
      <Route
        path="/candidates/:id"
        element={
          <RequireAuth>
            <CandidateDetail />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
