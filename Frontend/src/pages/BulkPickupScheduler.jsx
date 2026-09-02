import { useMemo, useState } from "react";
import {
  useBulkPickup,
  PICKUP_CATEGORIES,
  LOAD_SIZES,
  TIME_SLOTS,
} from "../context/BulkPickupContext";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  IconPackage,
  IconCalendar,
  IconClock,
  IconPin,
  IconX,
} from "../components/Icons";

const WARDS = [
  "MG Road (Ward 04)",
  "Koramangala (Ward 08)",
  "Indiranagar (Ward 12)",
  "Whitefield (Ward 15)",
];

const today = () => new Date().toISOString().slice(0, 10);

const emptyForm = {
  category: PICKUP_CATEGORIES[0],
  items: "",
  loadSize: "Small",
  quantity: 1,
  address: "",
  ward: WARDS[2],
  preferredDate: "",
  timeSlot: TIME_SLOTS[0],
  contactPhone: "",
  notes: "",
};

export default function BulkPickupScheduler() {
  const { pickups, schedulePickup, cancelPickup } = useBulkPickup();
  const { user } = useAuth();
  const { notify } = useToast();

  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  const setField = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));



  const myPickups = useMemo(
    () => pickups.filter((p) => p.requestedBy === user.name),
    [pickups, user.name]
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.items.trim()) return notify("Please describe the items for pickup.", "error");
    if (!form.address.trim()) return notify("Please provide a pickup address.", "error");
    if (!form.preferredDate) return notify("Please choose a preferred date.", "error");

    setSubmitting(true);
    const res = await schedulePickup({
      ...form,
      quantity: Math.max(1, parseInt(form.quantity, 10) || 1),
      items: form.items.trim(),
      address: form.address.trim(),
      requestedBy: user.name,
    });
    setSubmitting(false);

    if (res.success) {
      notify(`Bulk pickup ${res.pickup.id} scheduled successfully.`, "success");
      setForm(emptyForm);
    } else {
      notify(res.error || "Could not schedule pickup.", "error");
    }
  };

  const handleCancel = async (id) => {
    const res = await cancelPickup(id);
    if (res.success) notify(`Pickup ${id} cancelled.`, "info");
    else notify(res.error || "Could not cancel pickup.", "error");
  };

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <span className="eyebrow">Bulk & Bulky Waste</span>
          <h1>Schedule a Bulk Waste Pickup</h1>
          <p className="page-lead">
            Book a dedicated collection for large items that don't fit routine kerbside
            pickup — furniture, appliances, e-waste, construction debris and more.
          </p>
        </div>
      </div>

      <div className="bulk-layout">
        {/* ---- Scheduling form ---- */}
        <form onSubmit={handleSubmit} className="complaint-form bulk-form">
          <div className="field-group">
            <label>Waste Category</label>
            <select value={form.category} onChange={setField("category")}>
              {PICKUP_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div className="field-group">
            <label>Items to Collect</label>
            <textarea
              placeholder="e.g. 1 two-seater sofa, an old fridge, 3 broken chairs"
              value={form.items}
              onChange={setField("items")}
            />
          </div>

          <div className="bulk-form-row">
            <div className="field-group">
              <label>Estimated Load Size</label>
              <select value={form.loadSize} onChange={setField("loadSize")}>
                {LOAD_SIZES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div className="field-group">
              <label>Approx. Item Count</label>
              <input
                type="number"
                min="1"
                value={form.quantity}
                onChange={setField("quantity")}
              />
            </div>
          </div>

          <div className="field-group">
            <label>Pickup Address</label>
            <input
              type="text"
              placeholder="Street, landmark, building / gate no."
              value={form.address}
              onChange={setField("address")}
            />
          </div>

          <div className="bulk-form-row">
            <div className="field-group">
              <label>Ward / Zone</label>
              <select value={form.ward} onChange={setField("ward")}>
                {WARDS.map((w) => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </select>
            </div>
            <div className="field-group">
              <label>Contact Number</label>
              <input
                type="tel"
                placeholder="+91 ..."
                value={form.contactPhone}
                onChange={setField("contactPhone")}
              />
            </div>
          </div>

          <div className="bulk-form-row">
            <div className="field-group">
              <label>Preferred Date</label>
              <input
                type="date"
                min={today()}
                value={form.preferredDate}
                onChange={setField("preferredDate")}
              />
            </div>
            <div className="field-group">
              <label>Preferred Time Slot</label>
              <select value={form.timeSlot} onChange={setField("timeSlot")}>
                {TIME_SLOTS.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="field-group">
            <label>Access Notes (optional)</label>
            <textarea
              placeholder="e.g. items on 2nd floor, gate code 1234, call on arrival"
              value={form.notes}
              onChange={setField("notes")}
            />
          </div>



          <button type="submit" className="submit-complaint-btn" disabled={submitting}>
            <IconCalendar />
            {submitting ? "Scheduling..." : "Schedule Pickup"}
          </button>
        </form>

        {/* ---- Citizen's own requests ---- */}
        <div className="bulk-mine">
          <h2 className="bulk-mine-title">
            <IconPackage /> Your Pickup Requests
            <span className="badge-neutral">{myPickups.length}</span>
          </h2>

          {myPickups.length === 0 ? (
            <div className="empty-state">
              You haven't scheduled any bulk pickups yet. Use the form to book your first one.
            </div>
          ) : (
            <div className="bulk-mine-list">
              {myPickups.map((p) => (
                <div key={p.id} className="op-card bulk-card">
                  <div className="op-card-header">
                    <div>
                      <span className="op-id">{p.id}</span>
                      <h3 className="op-title">{p.category}</h3>
                      <span className="op-subtitle">{p.items}</span>
                    </div>
                    <span className={`op-status-badge status-${p.status.toLowerCase().replace(/ /g, "-")}`}>
                      {p.status}
                    </span>
                  </div>

                  <div className="op-card-body">
                    <div className="op-detail-row">
                      <span className="label"><IconPin /> Address</span>
                      <span className="value">{p.address}</span>
                    </div>
                    <div className="op-detail-row">
                      <span className="label"><IconCalendar /> Requested Date</span>
                      <span className="value">{p.preferredDate}</span>
                    </div>
                    <div className="op-detail-row">
                      <span className="label"><IconClock /> Slot</span>
                      <span className="value">{p.timeSlot}</span>
                    </div>
                    {p.scheduledDate && (
                      <div className="op-detail-row">
                        <span className="label">Confirmed For</span>
                        <span className="value font-bold">{p.scheduledDate}</span>
                      </div>
                    )}
                    <div className="op-detail-row">
                      <span className="label">Load / Items</span>
                      <span className="value">{p.loadSize} · {p.quantity} items</span>
                    </div>
                  </div>

                  {(p.status === "Requested" || p.status === "Scheduled") && (
                    <div className="op-card-footer">
                      <button className="cancel-btn btn-sm" onClick={() => handleCancel(p.id)}>
                        <IconX /> Cancel Request
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
