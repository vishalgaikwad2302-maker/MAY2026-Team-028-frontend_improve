import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { IconAlertCircle, IconBroom } from "../components/Icons";

const roleHome = { citizen: "/report", crew: "/crew", admin: "/dashboard" };

export default function Register() {
  const { register, user } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const role = "citizen";
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to={roleHome[user.role] || "/"} replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      setIsSubmitting(false);
      return;
    }

    try {
      // Public sign-up can create a citizen or crew account (chosen below).
      // The backend enforces this server-side too — it accepts citizen/crew
      // but always forces anything else (e.g. admin) down to citizen — so
      // this is a UX convenience, not the actual security guarantee.
      const regRes = await register({
        email: email.trim().toLowerCase(),
        password,
        full_name: fullName.trim(),
        phone: phone.trim() || null,
        role,
      });

      if (!regRes.success) {
        setError(regRes.error);
        notify(regRes.error, "error");
        return;
      }

      // register() now handles login + profile fetch internally.
      // regRes.role comes from /auth/me — the server's canonical value.
      notify(`Welcome to SmartSweep, ${regRes.name}!`, "success");
      navigate(roleHome[regRes.role] || "/", { replace: true });
    } catch (err) {
      const msg = err?.message || "Registration failed. Please check backend connection.";
      setError(msg);
      notify(msg, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <span className="brand-mark" style={{ display: "flex", margin: "0 auto 1rem" }}>
        <IconBroom />
      </span>
      <span className="eyebrow">Citizen Registration</span>
      <h1>SmartSweep</h1>
      <p className="login-sub">Create your citizen account to report issues & track cleanups</p>

      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          Full Name
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Enter your full name"
            required
            disabled={isSubmitting}
          />
        </label>

        <label>
          Email Address
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="e.g. citizen@example.com"
            required
            disabled={isSubmitting}
          />
        </label>

        <label>
          Phone Number (Optional)
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="e.g. +91 98765 43210"
            disabled={isSubmitting}
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Minimum 6 characters"
            required
            disabled={isSubmitting}
          />
        </label>

        {error && (
          <p className="loc-error">
            <IconAlertCircle /> {error}
          </p>
        )}

        <p style={{ color: "#888", fontSize: "0.85rem", marginTop: "-0.5rem" }}>
          Register as a Citizen to report garbage issues and track community cleanup progress.
          Field crew and administrative accounts are provisioned directly by Municipal Admins.
        </p>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating Account..." : "Create Account"}
        </button>

        <div style={{ textAlign: "center", marginTop: "1rem" }}>
          <p style={{ color: "#888", fontSize: "0.9rem" }}>
            Already have an account?{" "}
            <Link to="/login" style={{ color: "#38ef7d", fontWeight: "600" }}>
              Sign In
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
}
