// Lightweight stroke-icon set (Feather-style) used across SmartSweep.
// Kept in one file so the visual language stays consistent everywhere.

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  width: "1.2em",
  height: "1.2em",
};

export const IconHome = (props) => (
  <svg {...base} {...props}>
    <path d="M3 11.5 12 4l9 7.5" />
    <path d="M5.5 9.5V20h13V9.5" />
    <path d="M9.5 20v-6h5v6" />
  </svg>
);

export const IconReport = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v9M7.5 12h9" />
  </svg>
);

export const IconClipboard = (props) => (
  <svg {...base} {...props}>
    <rect x="5.5" y="4.5" width="13" height="16" rx="2" />
    <path d="M9 4.5h6a1 1 0 0 1 1 1V6H8V5.5a1 1 0 0 1 1-1Z" />
    <path d="M8.5 11h7M8.5 14.5h7M8.5 18h4" />
  </svg>
);

export const IconBroom = (props) => (
  <svg {...base} {...props}>
    <path d="M20 4 10.5 13.5" />
    <path d="M9 12 4 20l3 1 2.5-3.5" />
    <path d="M9 12c-1-1.4-.7-3 .6-4.1 1.4-1.2 3.4-1 4.4.4l1 1.4-3.9 3.3-2.1-1Z" />
  </svg>
);

export const IconGrid = (props) => (
  <svg {...base} {...props}>
    <rect x="4" y="4" width="7" height="7" rx="1.4" />
    <rect x="13" y="4" width="7" height="7" rx="1.4" />
    <rect x="4" y="13" width="7" height="7" rx="1.4" />
    <rect x="13" y="13" width="7" height="7" rx="1.4" />
  </svg>
);

export const IconLogOut = (props) => (
  <svg {...base} {...props}>
    <path d="M9 4.5H6a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 6 19.5h3" />
    <path d="M14.5 16 19 12l-4.5-4" />
    <path d="M19 12H9" />
  </svg>
);

export const IconSun = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
  </svg>
);

export const IconMoon = (props) => (
  <svg {...base} {...props}>
    <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4 6.8 6.8 0 0 0 20 14.5Z" />
  </svg>
);

export const IconPin = (props) => (
  <svg {...base} {...props}>
    <path d="M12 21s-6.5-6.1-6.5-11A6.5 6.5 0 0 1 18.5 10c0 4.9-6.5 11-6.5 11Z" />
    <circle cx="12" cy="10" r="2.3" />
  </svg>
);

export const IconCamera = (props) => (
  <svg {...base} {...props}>
    <path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2l1-2h7l1 2h2A1.5 1.5 0 0 1 20 8.5v9A1.5 1.5 0 0 1 18.5 19h-13A1.5 1.5 0 0 1 4 17.5v-9Z" />
    <circle cx="12" cy="12.5" r="3.4" />
  </svg>
);

export const IconUpload = (props) => (
  <svg {...base} {...props}>
    <path d="M12 16V4" />
    <path d="M7 8.5 12 4l5 4.5" />
    <path d="M4.5 15v3.5A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5V15" />
  </svg>
);

export const IconCheckCircle = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M8.5 12.3 11 14.7l4.8-5.4" />
  </svg>
);

export const IconUserPlus = (props) => (
  <svg {...base} {...props}>
    <circle cx="10" cy="9" r="3.2" />
    <path d="M4.5 19c.6-3 2.8-4.7 5.5-4.7s4.9 1.7 5.5 4.7" />
    <path d="M18 8.5v5M15.5 11h5" />
  </svg>
);

export const IconAlertTriangle = (props) => (
  <svg {...base} {...props}>
    <path d="M12 4.5 21 19.5H3L12 4.5Z" />
    <path d="M12 10v4.2M12 17v.01" />
  </svg>
);

export const IconArrowRight = (props) => (
  <svg {...base} {...props}>
    <path d="M4.5 12h14.5M13.5 6.5 20 12l-6.5 5.5" />
  </svg>
);

export const IconAlertCircle = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 8v4.5M12 16v.01" />
  </svg>
);

export const IconStar = (props) => (
  <svg {...base} {...props}>
    <path d="M12 3.8 14.5 9l5.7.8-4.1 4 1 5.7-5.1-2.7-5.1 2.7 1-5.7-4.1-4L9.5 9Z" />
  </svg>
);

export const IconSearch = (props) => (
  <svg {...base} {...props}>
    <circle cx="10.5" cy="10.5" r="6.5" />
    <path d="M19.5 19.5 15.3 15.3" />
  </svg>
);

export const IconSliders = (props) => (
  <svg {...base} {...props}>
    <path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h13M21 18h-1" />
    <circle cx="14.5" cy="6" r="2" />
    <circle cx="8.5" cy="12" r="2" />
    <circle cx="18.5" cy="18" r="2" />
  </svg>
);

export const IconX = (props) => (
  <svg {...base} {...props}>
    <path d="M6 6l12 12M18 6 6 18" />
  </svg>
);

export const IconRadar = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <circle cx="12" cy="12" r="4.5" />
    <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
    <path d="M12 3.5V1.5M20.5 12H12" />
  </svg>
);

export const IconTruck = (props) => (
  <svg {...base} {...props}>
    <rect x="1" y="3" width="15" height="13" rx="2" />
    <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
    <circle cx="5.5" cy="18.5" r="2.5" />
    <circle cx="18.5" cy="18.5" r="2.5" />
  </svg>
);

export const IconUsers = (props) => (
  <svg {...base} {...props}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

export const IconWrench = (props) => (
  <svg {...base} {...props}>
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
);

export const IconFeed = (props) => (
  <svg {...base} {...props}>
    <path d="M4 11a9 9 0 0 1 9 9" />
    <path d="M4 4a16 16 0 0 1 16 16" />
    <circle cx="5" cy="19" r="1" fill="currentColor" />
  </svg>
);

export const IconThumbsUp = (props) => (
  <svg {...base} {...props}>
    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
  </svg>
);

export const IconShieldCheck = (props) => (
  <svg {...base} {...props}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    <path d="M9 12l2 2 4-4" />
  </svg>
);

export const IconPlus = (props) => (
  <svg {...base} {...props}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const IconCalendar = (props) => (
  <svg {...base} {...props}>
    <rect x="4" y="5.5" width="16" height="15" rx="2" />
    <path d="M4 9.5h16M8 3.5v4M16 3.5v4" />
    <path d="M8 13h2M14 13h2M8 16.5h2M14 16.5h2" />
  </svg>
);

export const IconPackage = (props) => (
  <svg {...base} {...props}>
    <path d="M12 3 4 7v10l8 4 8-4V7l-8-4Z" />
    <path d="M4 7l8 4 8-4M12 11v10" />
    <path d="M8 5 16 9" />
  </svg>
);

export const IconClock = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </svg>
);

export const IconBell = (props) => (
  <svg {...base} {...props}>
    <path d="M6 9.5a6 6 0 0 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 13.5 6 9.5Z" />
    <path d="M10 19a2 2 0 0 0 4 0" />
  </svg>
);

export const IconChartBar = (props) => (
  <svg {...base} {...props}>
    <path d="M4 20V10M10 20V4M16 20v-7M4 20h16" strokeLinejoin="round" />
  </svg>
);

export const IconCheck = (props) => (
  <svg {...base} {...props}>
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

export const IconMenu = (props) => (
  <svg {...base} {...props}>
    <path d="M4 6h16M4 12h16M4 18h16" />
  </svg>
);

export const IconChevronRight = (props) => (
  <svg {...base} {...props}>
    <path d="m9 18 6-6-6-6" />
  </svg>
);

export const IconUser = (props) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="8" r="4" />
    <path d="M6 20v-2a6 6 0 0 1 12 0v2" />
  </svg>
);

