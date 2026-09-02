import { useMemo, useState } from "react";
import { useToast } from "../context/ToastContext";
import { IconBell, IconClock, IconAlertTriangle } from "../components/Icons";
import {
  WASTE_TYPES,
  DAYS,
  WARD_SCHEDULES,
  SCHEDULE_EXCEPTIONS,
  nextWeekdayOccurrence,
  nextMonthlyOccurrence,
  formatDate,
  daysFromToday,
} from "../utils/collectionSchedule";

export default function CollectionSchedule() {
  const { notify } = useToast();
  const [wardName, setWardName] = useState(WARD_SCHEDULES[0].ward);
  const [reminders, setReminders] = useState({ wet: false, dry: false, hazardous: false });

  const schedule = useMemo(
    () => WARD_SCHEDULES.find((w) => w.ward === wardName) || WARD_SCHEDULES[0],
    [wardName]
  );

  // The only "logic" on this page: find the next date matching each
  // category's pickup days. Everything else is static mock data.
  const nextDates = useMemo(
    () => ({
      wet: nextWeekdayOccurrence(schedule.wet),
      dry: nextWeekdayOccurrence(schedule.dry),
      hazardous: nextMonthlyOccurrence(schedule.hazardous),
    }),
    [schedule]
  );

  const toggleReminder = (key) => {
    setReminders((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      const label = WASTE_TYPES.find((w) => w.key === key)?.label;
      const date = nextDates[key];
      notify(
        next[key]
          ? `Reminder set for ${label} pickup${date ? ` — ${formatDate(date)}` : ""}.`
          : `Reminder turned off for ${label} pickup.`,
        next[key] ? "success" : "info"
      );
      return next;
    });
  };

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <span className="eyebrow">Citizen Services</span>
          <h1>Collection Schedule & Reminders</h1>
          <p className="page-lead">
            Pickup days for your ward, at a glance. Turn on a reminder for any waste category
            and we'll flag it here before the next scheduled collection.
          </p>
        </div>
      </div>

      <div className="field-group ward-select-group">
        <label htmlFor="ward-select">Your Ward</label>
        <select id="ward-select" value={wardName} onChange={(e) => setWardName(e.target.value)}>
          {WARD_SCHEDULES.map((w) => (
            <option key={w.ward} value={w.ward}>
              {w.ward}
            </option>
          ))}
        </select>
      </div>

      {/* Next pickup + reminder toggle, one card per waste type. This is
          the single source of truth for "when's my next pickup" — the
          old KPI strip above duplicated the same dates and was removed. */}
      <h2 className="section-heading">Next Pickup</h2>
      <div className="card-grid">
        {WASTE_TYPES.map((wt) => (
          <div className="op-card reminder-card" key={wt.key}>
            <div className="op-card-header">
              <div>
                <span className={`op-id waste-chip-plain ${wt.key}`}>{wt.label}</span>
                <p className="op-subtitle">{wt.hint}</p>
              </div>
            </div>
            <div className="op-card-body">
              <div className="op-detail-row">
                <span className="label"><IconClock /> Next pickup</span>
                <span className="value">
                  {formatDate(nextDates[wt.key])} ({daysFromToday(nextDates[wt.key])})
                </span>
              </div>
            </div>
            <button
              type="button"
              className={`reminder-toggle-btn ${reminders[wt.key] ? "active" : ""}`}
              onClick={() => toggleReminder(wt.key)}
              aria-pressed={reminders[wt.key]}
            >
              <IconBell />
              {reminders[wt.key] ? "Reminder On" : "Remind Me"}
            </button>
          </div>
        ))}
      </div>

      {/* Weekly calendar strip */}
      <h2 className="section-heading">This Week</h2>
      <div className="week-strip">
        {DAYS.map((day) => {
          const dayTypes = WASTE_TYPES.filter((wt) =>
            wt.key === "hazardous" ? false : schedule[wt.key].includes(day)
          );
          return (
            <div className={`week-cell ${dayTypes.length ? "has-pickup" : ""}`} key={day}>
              <span className="week-cell-day">{day.slice(0, 3)}</span>
              <div className="week-cell-chips">
                {dayTypes.length === 0 && <span className="week-cell-empty">—</span>}
                {dayTypes.map((wt) => (
                  <span key={wt.key} className={`waste-chip ${wt.key}`}>
                    {wt.label.split(" ")[0]}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Service exceptions, only rendered when there's something to show */}
      {SCHEDULE_EXCEPTIONS.length > 0 && (
        <>
          <h2 className="section-heading">Schedule Changes</h2>
          <div className="exceptions-list">
            {SCHEDULE_EXCEPTIONS.map((ex) => (
              <div className="exception-row" key={ex.date}>
                <IconAlertTriangle />
                <div>
                  <strong>
                    {new Date(ex.date).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })}
                  </strong>
                  <p>{ex.note}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
