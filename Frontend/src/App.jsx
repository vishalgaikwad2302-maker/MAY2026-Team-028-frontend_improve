import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import BottomNav from "./components/BottomNav";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Home from "./pages/Home";
import ReportComplaint from "./pages/ReportComplaint";
import MyComplaints from "./pages/MyComplaints";
import CrewTasks from "./pages/CrewTasks";
import SupervisorDashboard from "./pages/SupervisorDashboard";
import ComplaintDetail from "./pages/ComplaintDetail";
import WorkforceEquipment from "./pages/WorkforceEquipment";
import VehicleAssignment from "./pages/VehicleAssignment";
import BulkPickupScheduler from "./pages/BulkPickupScheduler";
import BulkPickupManagement from "./pages/BulkPickupManagement";
import PublicTransparencyFeed from "./pages/PublicTransparencyFeed";
import CollectionSchedule from "./pages/CollectionSchedule";
import ReportsTrends from "./pages/ReportsTrends";
import "./App.css";

function App() {
  return (
    <>
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/report" element={
            <ProtectedRoute allowedRoles={["citizen"]}><ReportComplaint /></ProtectedRoute>
          } />
          <Route path="/my-complaints" element={
            <ProtectedRoute allowedRoles={["citizen"]}><MyComplaints /></ProtectedRoute>
          } />
          <Route path="/crew" element={
            <ProtectedRoute allowedRoles={["crew"]}><CrewTasks /></ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute allowedRoles={["admin"]}><SupervisorDashboard /></ProtectedRoute>
          } />
          <Route path="/workforce" element={
            <ProtectedRoute allowedRoles={["admin"]}><WorkforceEquipment /></ProtectedRoute>
          } />
          <Route path="/vehicles" element={
            <ProtectedRoute allowedRoles={["admin"]}><VehicleAssignment /></ProtectedRoute>
          } />
          <Route path="/bulk-pickup" element={
            <ProtectedRoute allowedRoles={["citizen"]}><BulkPickupScheduler /></ProtectedRoute>
          } />
          <Route path="/bulk-pickup-manage" element={
            <ProtectedRoute allowedRoles={["admin"]}><BulkPickupManagement /></ProtectedRoute>
          } />
          <Route path="/feed" element={
            <ProtectedRoute><PublicTransparencyFeed /></ProtectedRoute>
          } />
          <Route path="/schedule" element={
            <ProtectedRoute allowedRoles={["citizen"]}><CollectionSchedule /></ProtectedRoute>
          } />
          <Route path="/reports" element={
            <ProtectedRoute allowedRoles={["admin"]}><ReportsTrends /></ProtectedRoute>
          } />
          <Route path="/complaint/:id" element={
            <ProtectedRoute><ComplaintDetail /></ProtectedRoute>
          } />
        </Routes>
      </main>
      <BottomNav />
    </>
  );
}

export default App;