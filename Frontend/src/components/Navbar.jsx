import { useState } from "react";
import { Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";
import { useAuth } from "../context/AuthContext";
import { IconBroom, IconMenu, IconX } from "./Icons";
import NavigationDrawer from "./NavigationDrawer";

const roleTags = {
  citizen: "Citizen",
  crew: "Crew Field",
  admin: "Admin Console",
};

export default function Navbar() {
  const { user } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <header className="navbar">
        <div className="navbar-left">
          {user && (
            <button
              className={`hamburger-btn ${drawerOpen ? "active" : ""}`}
              onClick={() => setDrawerOpen(!drawerOpen)}
              aria-label={drawerOpen ? "Close menu" : "Open menu"}
              aria-expanded={drawerOpen}
              title="Toggle navigation menu"
            >
              {drawerOpen ? <IconX /> : <IconMenu />}
            </button>
          )}

          <Link to={user ? "/" : "/login"} className="brand">
            <span className="brand-mark">
              <IconBroom />
            </span>
            <span className="brand-title">SmartSweep</span>
          </Link>
          {user && (
            <span className={`brand-role-tag role-tag-${user.role}`}>
              {roleTags[user.role] || user.role}
            </span>
          )}
        </div>

        <div className="navbar-right">
          {user && (
            <button
              className="user-profile-pill"
              onClick={() => setDrawerOpen(true)}
              title="Open profile and menu"
              aria-label="Open profile and menu"
            >
              <span className="user-avatar-mini">
                {user.name ? user.name[0].toUpperCase() : "U"}
              </span>
              <span className="user-name-text">{user.name}</span>
            </button>
          )}

          <ThemeToggle />
        </div>
      </header>

      {user && (
        <NavigationDrawer
          isOpen={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        />
      )}
    </>
  );
}