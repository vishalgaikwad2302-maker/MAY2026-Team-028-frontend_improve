# SmartSweep — Frontend

**SmartSweep** is a civic services platform for reporting and tracking garbage/waste-collection issues. This repository contains the React + Vite web app, with dedicated, role-based views for **Citizens**, **Cleanup Crew**, and **Ward Supervisors / Admins**.

> The app talks to the FastAPI backend in `../Backend` over JWT-authenticated REST calls (see `src/utils/api.js`). Complaint/task data that the backend doesn't yet own may still live in-memory (React Context) and reset on reload; auth (login/register/session) is fully backed by the real API and a database. Run the backend first (see `../Backend/README.md`) or auth calls will fail with a network error.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI Library | React 18 |
| Routing | React Router DOM |
| Build tool / dev server | Vite |
| Styling | CSS (dark/light theme toggle built in) |

---

## Project Structure

```
MAY2026-Team-028/
└── Frontend/
    ├── node_modules/      # installed dependencies (auto-generated, do not edit)
    ├── public/            # static assets
    ├── src/
    │   ├── components/    # reusable UI components (Navbar, BottomNav, etc.)
    │   ├── context/        # React Context providers (Auth, Theme, Complaints)
    │   ├── pages/          # route-level pages (Login, Report Issue, My Complaints,
    │   │                    #   Public Feed, Assigned Tasks, Vehicles, Bulk Pickup,
    │   │                    #   Supervisor Dashboard, Reports & Trends, etc.)
    │   ├── App.jsx
    │   └── main.jsx
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    └── .oxlintrc.json
```

---

## Prerequisites

Before you begin, make sure you have installed:

* **Node.js** v18 or later — [download here](https://nodejs.org/)
* **npm** (comes bundled with Node.js)

Check your versions with:

```bash
node -v
npm -v
```

---

## Installation & Run Instructions

### On Ubuntu / macOS

```bash
# 1. Navigate to the Frontend folder
#    (package.json lives inside Frontend/, not the repo root)
cd MAY2026-Team-028/Frontend

# 2. Install dependencies
npm install

# 3. Start the development server
npm run dev
```

### On Windows

```powershell
# 1. Clone the repository
git clone <repository-url>

# 2. Navigate to the Frontend folder
cd MAY2026-Team-028\Frontend

# 3. Install dependencies
npm install

# 4. Start the development server
npm run dev
```

Vite will start a local dev server and print a URL in the terminal, typically:

```
http://localhost:5173
```

Open that URL in your browser to view the app. The dev server supports hot-reload — changes to files in `src/` refresh automatically.

### Build for production (optional)

```bash
npm run build      # generates an optimized build in dist/
npm run preview    # preview the production build locally
```

---

## Logging In

Auth is backed by the real FastAPI backend (`../Backend`) — make sure it's running (`http://localhost:8000` by default) before signing in.

**Seeded demo accounts** (created automatically the first time the backend starts):

| Role | Email | Password |
|---|---|---|
| Citizen 1 (Sagnik) | `citizen@smartsweep.gov` | `citizen123` |
| Citizen 2 (Anita) | `anita@smartsweep.gov` | `anita123` |
| Citizen 3 (Mohammed) | `mohammed@smartsweep.gov` | `mohammed123` |
| Cleanup Crew | `crew@smartsweep.gov` | `crew123` |
| Ward Supervisor / Admin | `admin@smartsweep.gov` | `admin123` |

Sign in with the **email**, not a username — the login form takes an email address and password.

**Creating your own account:** the Register page (`/register`) lets you sign up as either a **Citizen** or a **Crew Member** — pick the account type at the top of the form. Admin accounts aren't available through sign-up; use the seeded `admin@smartsweep.gov` account above, or have an existing admin provision one.

---

## What's Implemented (Milestone 2)

- **Citizen:** report a garbage issue (location, description, hazard classification, photo upload), track "My Complaints," schedule a bulk waste pickup, and view the Public Transparency & Impact Feed.
- **Cleanup Crew:** view assigned tasks with hazard info, manage vehicle/fleet assignment, and manage bulk pickups.
- **Ward Supervisor / Admin:** supervisor dashboard for all complaints, fleet & vehicle assignment, bulk pickup management, and Reports & Trends analytics.
- All pages are linked and navigable across roles, with a dark/light theme toggle.

---

## Troubleshooting

* **`Failed to resolve import "react-router-dom"`** → Run `npm install` inside the `Frontend` folder to make sure all dependencies are installed.
* **Login/register fails with a network error** → The backend isn't running (or isn't reachable at `http://localhost:8000`). Start it per `../Backend/README.md`, and check its CORS_ORIGINS includes your Vite dev server URL.
* **Blank page on load** → Open the browser console (F12) to check for errors; this usually means a missing export or import somewhere in `src/`.
* **Port already in use** → Vite automatically tries the next available port; check the terminal output for the actual URL.
* **Clean reinstall** (if things get stuck):
  ```bash
  rm -rf node_modules package-lock.json
  npm install
  ```

---

## Notes

Auth (login, registration, session persistence) is fully integrated with the FastAPI backend and its database — there is no mock/local-only login path. Some other data (complaints, tasks, etc.) may still be backed by in-memory React Context depending on how far backend integration for that area has progressed; check the relevant Context provider in `src/context/` if you're unsure whether a given feature is live or local-only.
