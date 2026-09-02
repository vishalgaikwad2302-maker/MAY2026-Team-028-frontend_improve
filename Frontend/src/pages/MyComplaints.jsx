import { useEffect } from "react";
import { useComplaints } from "../context/ComplaintsContext";
import { useAuth } from "../context/AuthContext";
import ComplaintCard from "../components/ComplaintCard";

export default function MyComplaints() {
  const { complaints, refreshComplaints } = useComplaints();
  const { user } = useAuth();

  useEffect(() => {
    if (refreshComplaints) refreshComplaints();
  }, []);

  const myComplaints = complaints.filter(
    (c) => c.reportedBy === user?.name || c.reportedByUserId === user?.id
  );

  return (
    <div className="page">
      <h1>My Complaints</h1>
      {myComplaints.length === 0 ? (
        <p>No complaints submitted yet.</p>
      ) : (
        <div className="complaint-list grid-desktop">
          {myComplaints.map((c) => (
            <ComplaintCard key={c.id} complaint={c} />
          ))}
        </div>
      )}
    </div>
  );
}