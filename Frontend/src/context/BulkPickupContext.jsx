import { createContext, useContext, useEffect, useState } from "react";

const BulkPickupContext = createContext(null);

// Bulky-waste categories that don't fit routine kerbside collection.
export const PICKUP_CATEGORIES = [
  "Furniture",
  "Home Appliances",
  "E-Waste & Electronics",
  "Construction Debris",
  "Garden / Green Waste",
  "Mattress & Bedding",
  "Scrap Metal",
  "Other Bulky Items",
];

// Load bands drive the base fee and hint which vehicle can carry the load.
export const LOAD_SIZES = [
  { value: "Small", label: "Small — a few items (fits a van)" },
  { value: "Medium", label: "Medium — half a tipper load" },
  { value: "Large", label: "Large — full mini-tipper load" },
  { value: "Extra Large", label: "Extra Large — needs a compactor truck" },
];

export const TIME_SLOTS = [
  "Morning (08:00 - 11:00)",
  "Midday (11:00 - 14:00)",
  "Afternoon (14:00 - 17:00)",
  "Evening (17:00 - 20:00)",
];



const INITIAL_PICKUPS = [
  {
    id: "BP-1001",
    category: "Furniture",
    items: "2-seater sofa, wooden dining table, 3 broken chairs",
    loadSize: "Medium",
    quantity: 6,
    address: "MG Road, Near Bus Stop",
    ward: "MG Road (Ward 04)",
    preferredDate: "2026-07-24",
    timeSlot: "Morning (08:00 - 11:00)",
    contactPhone: "+91 90000 11111",
    notes: "Items are on the ground floor, easy to load.",
    requestedBy: "Anita Rao",
    status: "Scheduled",
    scheduledDate: "2026-07-24",
    assignedCrew: "Ramesh Kumar",
    assignedVehicle: "KA-01-EV-9012",
    createdAt: "2026-07-19",
  },
  {
    id: "BP-1002",
    category: "E-Waste & Electronics",
    items: "Old refrigerator, 2 CRT monitors, tangle of cables",
    loadSize: "Small",
    quantity: 4,
    address: "5th Cross, Indiranagar",
    ward: "Indiranagar (Ward 12)",
    preferredDate: "2026-07-26",
    timeSlot: "Afternoon (14:00 - 17:00)",
    contactPhone: "+91 90000 22222",
    notes: "Refrigerator needs 2 people to lift. Please handle gas safely.",
    requestedBy: "Mohammed Iqbal",
    status: "Requested",
    scheduledDate: null,
    assignedCrew: "Unassigned",
    assignedVehicle: "Unassigned",
    createdAt: "2026-07-21",
  },
  {
    id: "BP-1003",
    category: "Construction Debris",
    items: "Bathroom renovation rubble, ~15 cement bags of debris",
    loadSize: "Large",
    quantity: 15,
    address: "80 Feet Road, Koramangala",
    ward: "Koramangala (Ward 08)",
    preferredDate: "2026-07-22",
    timeSlot: "Midday (11:00 - 14:00)",
    contactPhone: "+91 90000 33333",
    notes: "Debris bagged and stacked near the gate.",
    requestedBy: "Sagnik Halder",
    status: "Collected",
    scheduledDate: "2026-07-20",
    assignedCrew: "Suresh Patil",
    assignedVehicle: "KA-01-EA-4821",
    createdAt: "2026-07-17",
  },
];

export function BulkPickupProvider({ children }) {
  const [pickups, setPickups] = useState(() => {
    const saved = localStorage.getItem("smartsweep-bulk-pickups");
    return saved ? JSON.parse(saved) : INITIAL_PICKUPS;
  });

  useEffect(() => {
    localStorage.setItem("smartsweep-bulk-pickups", JSON.stringify(pickups));
  }, [pickups]);

  // Mutators are Promise-returning (mirroring ComplaintsContext) so call sites
  // already `await`, and swapping the body for a FastAPI `fetch()` later won't
  // touch any component.
  const schedulePickup = (data) =>
    new Promise((resolve) => {
      setPickups((prev) => {
        const nextNum =
          prev.reduce((max, p) => {
            const n = parseInt(String(p.id).replace("BP-", ""), 10);
            return Number.isNaN(n) ? max : Math.max(max, n);
          }, 1000) + 1;
        const newPickup = {
          id: `BP-${nextNum}`,
          status: "Requested",
          scheduledDate: null,
          assignedCrew: "Unassigned",
          assignedVehicle: "Unassigned",
          createdAt: new Date().toISOString().slice(0, 10),
          ...data,
        };
        resolve({ success: true, pickup: newPickup });
        return [newPickup, ...prev];
      });
    });

  // Generic partial update — every other mutator builds on this one.
  const updatePickup = (id, updates) =>
    new Promise((resolve) => {
      setPickups((prev) => {
        if (!prev.some((p) => p.id === id)) {
          resolve({ success: false, error: "Pickup request not found." });
          return prev;
        }
        resolve({ success: true });
        return prev.map((p) => (p.id === id ? { ...p, ...updates } : p));
      });
    });

  // A citizen may withdraw a request only before the crew is out collecting.
  const cancelPickup = (id) =>
    new Promise((resolve) => {
      setPickups((prev) => {
        const target = prev.find((p) => p.id === id);
        if (!target) {
          resolve({ success: false, error: "Pickup request not found." });
          return prev;
        }
        if (target.status !== "Requested" && target.status !== "Scheduled") {
          resolve({
            success: false,
            error: "Only requested or scheduled pickups can be cancelled.",
          });
          return prev;
        }
        resolve({ success: true });
        return prev.map((p) => (p.id === id ? { ...p, status: "Cancelled" } : p));
      });
    });

  return (
    <BulkPickupContext.Provider
      value={{ pickups, schedulePickup, updatePickup, cancelPickup }}
    >
      {children}
    </BulkPickupContext.Provider>
  );
}

export const useBulkPickup = () => useContext(BulkPickupContext);
