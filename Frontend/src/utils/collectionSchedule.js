// Static, mock collection-schedule data for the Collection Schedule +
// Reminder feature (#15). There's no backend yet, so this is a hardcoded
// per-ward timetable — the only "logic" here is finding the next weekday
// that matches a ward's pickup days, which is plain date math, not AI.

export const WASTE_TYPES = [
  { key: "wet", label: "Wet Waste", hint: "Kitchen scraps, food waste, garden trimmings" },
  { key: "dry", label: "Dry Waste", hint: "Paper, plastic, glass, metal — rinsed & dry" },
  { key: "hazardous", label: "Hazardous / E-Waste", hint: "Batteries, medicines, electronics, bulbs" },
];

export const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

// Each ward's weekly pickup days per waste type. Hazardous/e-waste runs
// once a month on a fixed weekday instead of weekly.
export const WARD_SCHEDULES = [
  {
    ward: "MG Road (Ward 04)",
    wet: ["Monday", "Wednesday", "Friday"],
    dry: ["Tuesday", "Saturday"],
    hazardous: { day: "Saturday", occurrence: "First" },
  },
  {
    ward: "Indiranagar (Ward 12)",
    wet: ["Monday", "Wednesday", "Friday"],
    dry: ["Thursday"],
    hazardous: { day: "Sunday", occurrence: "First" },
  },
  {
    ward: "Koramangala (Ward 08)",
    wet: ["Tuesday", "Thursday", "Saturday"],
    dry: ["Monday"],
    hazardous: { day: "Saturday", occurrence: "Third" },
  },
  {
    ward: "Jayanagar (Ward 15)",
    wet: ["Sunday", "Tuesday", "Thursday", "Saturday"],
    dry: ["Wednesday"],
    hazardous: { day: "Sunday", occurrence: "Third" },
  },
];

// A couple of static service-alert style exceptions to show alongside the
// regular schedule — purely illustrative, not tied to any real calendar.
export const SCHEDULE_EXCEPTIONS = [
  {
    date: "2026-08-15",
    note: "Independence Day — no collection. Pickup shifts to the next working day.",
  },
  {
    date: "2026-08-29",
    note: "Ganesh Chaturthi — dry waste collection only; wet waste resumes the day after.",
  },
];

/** Next calendar date (today or later) that falls on one of `weekdays`. */
export function nextWeekdayOccurrence(weekdays, from = new Date()) {
  if (!weekdays?.length) return null;
  const base = new Date(from);
  base.setHours(0, 0, 0, 0);
  for (let offset = 0; offset < 14; offset++) {
    const candidate = new Date(base);
    candidate.setDate(base.getDate() + offset);
    if (weekdays.includes(DAYS[candidate.getDay()])) return candidate;
  }
  return null;
}

/** Next date matching the Nth-weekday-of-the-month rule used for hazardous pickups. */
export function nextMonthlyOccurrence({ day, occurrence }, from = new Date()) {
  const ordinals = { First: 0, Second: 1, Third: 2, Fourth: 3 };
  const targetDow = DAYS.indexOf(day);
  const nth = ordinals[occurrence] ?? 0;

  const monthlyDateFor = (year, month) => {
    const first = new Date(year, month, 1);
    const firstTargetDow = (targetDow - first.getDay() + 7) % 7;
    const date = new Date(year, month, 1 + firstTargetDow + nth * 7);
    return date;
  };

  const today = new Date(from);
  today.setHours(0, 0, 0, 0);
  let result = monthlyDateFor(today.getFullYear(), today.getMonth());
  if (result < today) {
    result = monthlyDateFor(today.getFullYear(), today.getMonth() + 1);
  }
  return result;
}

export function formatDate(date) {
  if (!date) return "—";
  return date.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}

export function daysFromToday(date) {
  if (!date) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((date - today) / (1000 * 60 * 60 * 24));
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  return `In ${diff} days`;
}
