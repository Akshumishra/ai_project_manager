import { Link } from "react-router-dom";

export default function AddProject() {
  return (
    <div className="shell narrow" style={{ paddingTop: "48px" }}>
      <div className="card center-card">
        <h1 className="hero-title">AI Project Manager</h1>
        <p className="page-copy">
          Use AI-driven agents to gather requirements anddraft your technical
          documentation in minutes.
        </p>
        <Link to="/create-project" className="primary-btn" style={{ textDecoration: "none" }}>
          Create a new project
        </Link>
      </div>
    </div>
  );
}
