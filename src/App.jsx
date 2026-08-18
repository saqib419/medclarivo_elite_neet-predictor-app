import { Routes, Route } from "react-router-dom";
import TopBar from "./components/TopBar.jsx";
import BottomNav from "./components/BottomNav.jsx";
import HomeDashboard from "./pages/HomeDashboard.jsx";
import PredictorForm from "./pages/PredictorForm.jsx";
import MatchingColleges from "./pages/MatchingColleges.jsx";
import CollegesBrowse from "./pages/CollegesBrowse.jsx";
import CollegeDetails from "./pages/CollegeDetails.jsx";
import Profile from "./pages/Profile.jsx";

const TITLES = {
  "/": "MedPredict",
  "/predict": "MedPredict",
  "/results": "MedPredict",
  "/colleges": "MedPredict",
  "/profile": "MedPredict",
};

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-on-background font-sans">
      <Routes>
        <Route path="/" element={<><TopBar /><main className="flex-1"><HomeDashboard /></main></>} />
        <Route path="/predict" element={<><TopBar /><main className="flex-1"><PredictorForm /></main></>} />
        <Route path="/results" element={<><TopBar /><main className="flex-1"><MatchingColleges /></main></>} />
        <Route path="/colleges" element={<><TopBar /><main className="flex-1"><CollegesBrowse /></main></>} />
        <Route path="/college/:slug" element={<><TopBar back /><main className="flex-1"><CollegeDetails /></main></>} />
        <Route path="/profile" element={<><TopBar /><main className="flex-1"><Profile /></main></>} />
      </Routes>
      <BottomNav />
    </div>
  );
}
