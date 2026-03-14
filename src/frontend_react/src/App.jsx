import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";
import AddProject from "./pages/AddProject";
import CreateProject from "./pages/CreateProject";
import RequirementAgent from "./pages/RequirementAgent";
import TechDoc from "./pages/TechDoc";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/add-project" replace />} />
        <Route path="/add-project" element={<AddProject />} />
        <Route path="/create-project" element={<CreateProject />} />
        <Route path="/requirement-agent" element={<RequirementAgent />} />
        <Route path="/tech-doc" element={<TechDoc />} />
      </Routes>
    </BrowserRouter>
  );
}
