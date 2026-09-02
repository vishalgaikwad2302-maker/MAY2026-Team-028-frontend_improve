import { createContext, useContext, useState, useEffect } from "react";
import { apiFetch } from "../utils/api";

const OperationalContext = createContext(null);

const INITIAL_WORKFORCE = [
  {
    id: "W-101",
    name: "Suresh Patil",
    role: "Crew Lead & Heavy Sweeper",
    shift: "Morning (06:00 - 14:00)",
    status: "On Duty",
    ward: "Indiranagar (Ward 12)",
    phone: "+91 98765 43210",
    assignedTask: "MG Road Dump Cleanup (#0001)",
  },
  {
    id: "W-102",
    name: "Ramesh Kumar",
    role: "Sanitation Specialist",
    shift: "Morning (06:00 - 14:00)",
    status: "On Duty",
    ward: "Indiranagar (Ward 12)",
    phone: "+91 98765 43211",
    assignedTask: "5th Cross Park Clearance (#0002)",
  },
  {
    id: "W-103",
    name: "Anand Verma",
    role: "Compactor Operator",
    shift: "Evening (14:00 - 22:00)",
    status: "On Duty",
    ward: "Koramangala (Ward 08)",
    phone: "+91 98765 43212",
    assignedTask: "Standby for Heavy Loads",
  },
  {
    id: "W-104",
    name: "Priya Sharma",
    role: "Safety & Biohazard Inspector",
    shift: "Morning (06:00 - 14:00)",
    status: "Available",
    ward: "MG Road (Ward 04)",
    phone: "+91 98765 43213",
    assignedTask: "Routine Area Inspection",
  },
  {
    id: "W-105",
    name: "Deepak Gowda",
    role: "Rapid Response Crew",
    shift: "Night (22:00 - 06:00)",
    status: "Off Duty",
    ward: "Whitefield (Ward 15)",
    phone: "+91 98765 43214",
    assignedTask: "None",
  },
];

const INITIAL_EQUIPMENT = [
  {
    id: "EQ-201",
    name: "High-Pressure Hydraulic Washer X1",
    category: "Heavy Machinery",
    status: "In Use",
    condition: "Optimal",
    location: "MG Road Sector 4",
    assignedTo: "Suresh Patil",
    stockTotal: 4,
    stockAvailable: 2,
  },
  {
    id: "EQ-202",
    name: "Automated Road Sweeper Machine",
    category: "Vehicular Equipment",
    status: "Available",
    condition: "Good",
    location: "Central Depot",
    assignedTo: "Unassigned",
    stockTotal: 3,
    stockAvailable: 3,
  },
  {
    id: "EQ-203",
    name: "Heavy Duty Biohazard Drums & Grabbers",
    category: "Safety Gear",
    status: "In Use",
    condition: "Good",
    location: "Indiranagar 5th Cross",
    assignedTo: "Ramesh Kumar",
    stockTotal: 15,
    stockAvailable: 8,
  },
  {
    id: "EQ-204",
    name: "Industrial Odor Neutralizer Sprayer",
    category: "Sanitation Tools",
    status: "Maintenance",
    condition: "Under Repair",
    location: "Depot Workshop",
    assignedTo: "Unassigned",
    stockTotal: 5,
    stockAvailable: 1,
  },
  {
    id: "EQ-205",
    name: "Commercial Trash Compactor Unit",
    category: "Waste Processing",
    status: "Available",
    condition: "Excellent",
    location: "Ward 08 Transfer Station",
    assignedTo: "Anand Verma",
    stockTotal: 2,
    stockAvailable: 2,
  },
];

const INITIAL_VEHICLES = [
  {
    id: "V-301",
    plateNo: "KA-01-EA-4821",
    model: "Heavy Hydraulic Compactor Truck",
    type: "Compactor",
    capacity: "8.5 Tons",
    fuelLevel: 82,
    status: "En Route",
    ward: "Indiranagar (Ward 12)",
    driver: "Anand Verma",
    assignedTask: "MG Road Blackspot Clearing (#0001)",
    lastMaintenance: "2026-06-10",
  },
  {
    id: "V-302",
    plateNo: "KA-01-EV-9012",
    model: "Electric Zero-Emission Tipper Truck",
    type: "Mini Tipper",
    capacity: "2.5 Tons",
    fuelLevel: 95,
    status: "On Site",
    ward: "Indiranagar (Ward 12)",
    driver: "Suresh Patil",
    assignedTask: "5th Cross Park Clearance (#0002)",
    lastMaintenance: "2026-06-15",
  },
  {
    id: "V-303",
    plateNo: "KA-05-MS-1104",
    model: "Mechanical Vacuum Road Sweeper",
    type: "Road Sweeper",
    capacity: "4.0 Tons",
    fuelLevel: 65,
    status: "Available",
    ward: "MG Road (Ward 04)",
    driver: "Unassigned",
    assignedTask: "Standby at Central Depot",
    lastMaintenance: "2026-06-01",
  },
  {
    id: "V-304",
    plateNo: "KA-03-IV-7740",
    model: "Supervisor Field Inspection Van",
    type: "Inspection Van",
    capacity: "5 Passengers",
    fuelLevel: 45,
    status: "In Depot",
    ward: "Koramangala (Ward 08)",
    driver: "Priya Sharma",
    assignedTask: "Ward Patrol",
    lastMaintenance: "2026-05-20",
  },
  {
    id: "V-305",
    plateNo: "KA-02-HT-3319",
    model: "Bio-Waste Sealed Transporter",
    type: "Hazmat Van",
    capacity: "3.0 Tons",
    fuelLevel: 30,
    status: "Maintenance",
    ward: "Whitefield (Ward 15)",
    driver: "Unassigned",
    assignedTask: "Hydraulic Pump Repair",
    lastMaintenance: "2026-06-18",
  },
];

const INITIAL_FEED = [
  {
    id: "F-501",
    title: "MG Road Overflowing Dump Clearance",
    caseNo: "#0001",
    location: "MG Road, Near Bus Stop",
    ward: "Ward 04",
    resolvedBy: "Crew Alpha (Led by Suresh Patil)",
    completedAt: "2026-06-21 11:30 AM",
    wasteRemoved: "1.4 Tons",
    hazardAddressed: "Foul Smell & Obstruction",
    beforePhoto: "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=600&q=80",
    afterPhoto: "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=600&q=80",
    applauds: 42,
    verified: true,
    comments: [
      { id: 1, user: "Anita Rao", text: "Incredible transformation! Thank you so much for the swift action.", time: "2 hours ago" },
      { id: 2, user: "Rohan M.", text: "The area smells fresh now. Great effort by the SmartSweep team!", time: "1 hour ago" },
    ],
  },
  {
    id: "F-502",
    title: "5th Cross Park Illegal Dumping Remediation",
    caseNo: "#0002",
    location: "5th Cross, Indiranagar",
    ward: "Ward 12",
    resolvedBy: "Crew Beta (Ramesh Kumar & Vehicle KA-01-EV-9012)",
    completedAt: "2026-06-20 04:15 PM",
    wasteRemoved: "0.8 Tons",
    hazardAddressed: "Mosquito Breeding Site Cleared",
    beforePhoto: "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=600&q=80",
    afterPhoto: "https://images.unsplash.com/photo-1519331379826-f10be5486c6f?auto=format&fit=crop&w=600&q=80",
    applauds: 29,
    verified: true,
    comments: [
      { id: 1, user: "Mohammed Iqbal", text: "Park entrance is completely clear. Kids are back playing here!", time: "1 day ago" },
    ],
  },
  {
    id: "F-503",
    title: "Koramangala Commercial Hub De-littering",
    caseNo: "#0003",
    location: "80 Feet Road, Koramangala",
    ward: "Ward 08",
    resolvedBy: "Night Sanitation Fleet",
    completedAt: "2026-06-19 07:00 AM",
    wasteRemoved: "2.1 Tons",
    hazardAddressed: "Stormwater Drain Unblocked",
    beforePhoto: "https://images.unsplash.com/photo-1503596476-1c12a8ba09a9?auto=format&fit=crop&w=600&q=80",
    afterPhoto: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80",
    applauds: 58,
    verified: true,
    comments: [
      { id: 1, user: "Kavita S.", text: "Awesome night drive cleanup!", time: "2 days ago" },
    ],
  },
];

export function OperationalProvider({ children }) {
  const [workforce, setWorkforce] = useState(() => {
    const saved = localStorage.getItem("smartsweep-workforce");
    return saved ? JSON.parse(saved) : INITIAL_WORKFORCE;
  });

  const [equipment, setEquipment] = useState(() => {
    const saved = localStorage.getItem("smartsweep-equipment");
    return saved ? JSON.parse(saved) : INITIAL_EQUIPMENT;
  });

  const [vehicles, setVehicles] = useState(() => {
    const saved = localStorage.getItem("smartsweep-vehicles");
    return saved ? JSON.parse(saved) : INITIAL_VEHICLES;
  });

  const [feed, setFeed] = useState(() => {
    const saved = localStorage.getItem("smartsweep-feed");
    return saved ? JSON.parse(saved) : INITIAL_FEED;
  });

  useEffect(() => {
    localStorage.setItem("smartsweep-workforce", JSON.stringify(workforce));
  }, [workforce]);

  useEffect(() => {
    localStorage.setItem("smartsweep-equipment", JSON.stringify(equipment));
  }, [equipment]);

  useEffect(() => {
    localStorage.setItem("smartsweep-vehicles", JSON.stringify(vehicles));
  }, [vehicles]);

  useEffect(() => {
    localStorage.setItem("smartsweep-feed", JSON.stringify(feed));
  }, [feed]);

  // Workforce Actions
  const updateWorkerStatus = (id, newStatus, assignedTask) => {
    setWorkforce((prev) =>
      prev.map((w) => (w.id === id ? { ...w, status: newStatus, assignedTask: assignedTask ?? w.assignedTask } : w))
    );
  };

  const addWorker = async (workerData) => {
    try {
      const payload = {
        full_name: workerData.name,
        email: workerData.email || undefined,
        password: workerData.password || "crew123",
        phone: workerData.phone || undefined,
        role_title: workerData.role,
        ward_id: 1,
        status: "available",
      };

      const res = await apiFetch("/resources/workers", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const newWorker = {
        id: res?.data?.id ? `W-${res.data.id}` : `W-${100 + workforce.length + 1}`,
        status: "Available",
        assignedTask: "None",
        ...workerData,
      };

      setWorkforce((prev) => [newWorker, ...prev]);
      return { success: true, worker: newWorker };
    } catch {
      // Fallback for local state
      const newWorker = {
        id: `W-${100 + workforce.length + 1}`,
        status: "Available",
        assignedTask: "None",
        ...workerData,
      };
      setWorkforce((prev) => [newWorker, ...prev]);
      return { success: true, worker: newWorker };
    }
  };

  // Equipment Actions
  const updateEquipmentStatus = (id, status, assignedTo) => {
    setEquipment((prev) =>
      prev.map((eq) => {
        if (eq.id === id) {
          const isNowAvailable = status === "Available";
          const wasAvailable = eq.status === "Available";
          let availableDiff = 0;
          if (isNowAvailable && !wasAvailable) availableDiff = 1;
          if (!isNowAvailable && wasAvailable) availableDiff = -1;

          return {
            ...eq,
            status,
            assignedTo: assignedTo !== undefined ? assignedTo : eq.assignedTo,
            stockAvailable: Math.max(0, Math.min(eq.stockTotal, eq.stockAvailable + availableDiff)),
          };
        }
        return eq;
      })
    );
  };

  const addEquipment = (eqData) => {
    const newEq = {
      id: `EQ-${200 + equipment.length + 1}`,
      status: "Available",
      condition: "New",
      stockAvailable: parseInt(eqData.stockTotal || 1, 10),
      ...eqData,
    };
    setEquipment((prev) => [newEq, ...prev]);
  };

  // Vehicle Actions
  const updateVehicleStatus = (id, status, driver, assignedTask, ward) => {
    setVehicles((prev) =>
      prev.map((v) => {
        if (v.id === id) {
          return {
            ...v,
            ...(status && { status }),
            ...(driver !== undefined && { driver }),
            ...(assignedTask !== undefined && { assignedTask }),
            ...(ward !== undefined && { ward }),
          };
        }
        return v;
      })
    );
  };

  const addVehicle = (vData) => {
    const newV = {
      id: `V-${300 + vehicles.length + 1}`,
      status: "Available",
      fuelLevel: 100,
      lastMaintenance: new Date().toISOString().slice(0, 10),
      ...vData,
    };
    setVehicles((prev) => [newV, ...prev]);
  };

  // Transparency Feed Actions
  const applaudPost = (id) => {
    setFeed((prev) =>
      prev.map((f) => (f.id === id ? { ...f, applauds: f.applauds + 1 } : f))
    );
  };

  const addCommentToFeed = (feedId, userName, commentText) => {
    setFeed((prev) =>
      prev.map((f) => {
        if (f.id === feedId) {
          const newComment = {
            id: Date.now(),
            user: userName || "Anonymous Citizen",
            text: commentText,
            time: "Just now",
          };
          return { ...f, comments: [...f.comments, newComment] };
        }
        return f;
      })
    );
  };

  const addFeedPost = (postData) => {
    const newPost = {
      id: `F-${500 + feed.length + 1}`,
      completedAt: new Date().toLocaleString(),
      applauds: 1,
      verified: true,
      comments: [],
      ...postData,
    };
    setFeed((prev) => [newPost, ...prev]);
  };

  return (
    <OperationalContext.Provider
      value={{
        workforce,
        equipment,
        vehicles,
        feed,
        updateWorkerStatus,
        addWorker,
        updateEquipmentStatus,
        addEquipment,
        updateVehicleStatus,
        addVehicle,
        applaudPost,
        addCommentToFeed,
        addFeedPost,
      }}
    >
      {children}
    </OperationalContext.Provider>
  );
}

export const useOperational = () => useContext(OperationalContext);
