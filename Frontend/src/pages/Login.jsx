import { useState } from "react";
import { Link, Navigate, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { IconAlertCircle, IconBroom } from "../components/Icons";

const roleHome = { citizen: "/report", crew: "/crew", admin: "/dashboard" };

export default function Login() {
  const { login, user } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to={roleHome[user.role] || "/"} replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      const result = await login(email, password);
      if (!result.success) {
        setError(result.error);
        notify(result.error, "error");
        return;
      }
      notify(`Welcome back, ${result.name}`, "success");
      navigate(location.state?.from || roleHome[result.role] || "/", { replace: true });
    } catch (err) {
      const msg = err?.message || "Authentication failed. Make sure backend is running.";
      setError(msg);
      notify(msg, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <span className="brand-mark" style={{ display: "flex", margin: "0 auto 1rem" }}><IconBroom /></span>
      <span className="eyebrow">Restricted Access</span>
      <h1>SmartSweep</h1>
      <p className="login-sub">Sign in to continue</p>

      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            required
            disabled={isSubmitting}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            required
            disabled={isSubmitting}
          />
        </label>
        {error && <p className="loc-error"><IconAlertCircle /> {error}</p>}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Authenticating..." : "Access System"}
        </button>

        <div style={{ textAlign: "center", marginTop: "1rem" }}>
          <p style={{ color: "#888", fontSize: "0.9rem" }}>
            Don't have an account?{" "}
            <Link to="/register" style={{ color: "#38ef7d", fontWeight: "600" }}>
              Create Account
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
}
