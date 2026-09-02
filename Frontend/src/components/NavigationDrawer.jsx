import { useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import ThemeToggle from "./ThemeToggle";
import {
  IconHome,
  IconReport,
  IconClipboard,
  IconBroom,
  IconGrid,
  IconLogOut,
  IconUsers,
  IconTruck,
  IconFeed,
  IconPackage,
  IconCalendar,
  IconChartBar,
  IconX,
  IconChevronRight,
} from "./Icons";

const roleNavigation = {
  citizen: [
    {
      section: "Quick Access",
      links: [
        { to: "/", label: "Home Overview", icon: IconHome },
        { to: "/report", label: "Report New Issue", icon: IconReport, highlight: true },
        { to: "/my-complaints", label: "My Complaints", icon: IconClipboard },
      ],
    },
    {
      section: "Community & Services",
      links: [
        { to: "/bulk-pickup", label: "Bulk Pickup", icon: IconPackage },
        { to: "/schedule", label: "Collection Schedule", icon: IconCalendar },
        { to: "/feed", label: "Public Feed", icon: IconFeed },
      ],
    },
  ],
  crew: [
    {
      section: "Field Operations",
      links: [
        { to: "/", label: "Home Overview", icon: IconHome },
        { to: "/crew", label: "Assigned Tasks", icon: IconBroom, highlight: true },
        { to: "/feed", label: "Public Feed", icon: IconFeed },
      ],
    },
  ],
  admin: [
    {
      section: "Executive Dashboard",
      links: [
        { to: "/", label: "Home Overview", icon: IconHome },
        { to: "/dashboard", label: "Supervisor Dashboard", icon: IconGrid, highlight: true },
        { to: "/reports", label: "Reports & Analytics", icon: IconChartBar },
      ],
    },
    {
      section: "Management & Operations",
      links: [
        { to: "/workforce", label: "Workforce & Equipment", icon: IconUsers },
        { to: "/vehicles", label: "Fleet Dispatch", icon: IconTruck },
        { to: "/bulk-pickup-manage", label: "Bulk Requests", icon: IconPackage },
        { to: "/feed", label: "Public Feed", icon: IconFeed },
      ],
    },
  ],
};

const roleDisplayNames = {
  citizen: "Citizen",
  crew: "Crew Member",
  admin: "Administrator",
};

export default function NavigationDrawer({ isOpen, onClose }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { notify } = useToast();
  const prevPathRef = useRef(location.pathname);

  // Close only when route actually changes
  useEffect(() => {
    if (prevPathRef.current !== location.pathname) {
      prevPathRef.current = location.pathname;
      if (isOpen) {
        onClose();
      }
    }
  }, [location.pathname, isOpen, onClose]);

  // Handle ESC key and body scroll lock
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    } else {
      document.body.style.overflow = "";
    }

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!user) return null;

  const handleLogout = () => {
    onClose();
    logout();
    notify("Logged out successfully", "info");
    navigate("/login", { replace: true });
  };

  const sections = roleNavigation[user.role] || [];
  const initials = user.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className={`drawer-backdrop ${isOpen ? "open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <aside
        className={`drawer-panel ${isOpen ? "open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation Menu"
      >
        {/* Header with User Info */}
        <div className="drawer-header">
          <div className="drawer-user-info">
            <div className="drawer-avatar">{initials}</div>
            <div className="drawer-user-details">
              <span className="drawer-user-name">{user.name}</span>
              <span className={`drawer-role-badge badge-${user.role}`}>
                {roleDisplayNames[user.role] || user.role}
              </span>
            </div>
          </div>
          <button
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close navigation menu"
            title="Close menu"
          >
            <IconX />
          </button>
        </div>

        {/* Scrollable Nav Items */}
        <div className="drawer-body">
          {sections.map((sec, idx) => (
            <div key={idx} className="drawer-section">
              <div className="drawer-section-title">{sec.section}</div>
              <div className="drawer-links">
                {sec.links.map((link) => {
                  const isActive = location.pathname === link.to;
                  const Icon = link.icon;
                  return (
                    <Link
                      key={link.to}
                      to={link.to}
                      onClick={onClose}
                      className={`drawer-nav-item ${isActive ? "active" : ""} ${
                        link.highlight ? "highlight" : ""
                      }`}
                    >
                      <span className="drawer-icon-wrap">
                        <Icon />
                      </span>
                      <span className="drawer-item-label">{link.label}</span>
                      <IconChevronRight className="drawer-chevron" />
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Footer Actions */}
        <div className="drawer-footer">
          <div className="drawer-footer-row">
            <div className="drawer-theme-wrap">
              <span className="drawer-footer-label">Appearance</span>
              <ThemeToggle />
            </div>
            <button className="drawer-logout-btn" onClick={handleLogout}>
              <IconLogOut />
              <span>Log Out</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
