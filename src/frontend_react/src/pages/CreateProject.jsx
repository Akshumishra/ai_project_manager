import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createProjectRequest, DEFAULT_USER_ID } from "../api";
import { setActiveProject, setUserBackground } from "../storage";

export default function CreateProject() {
  const navigate = useNavigate();
  const [projectTitle, setProjectTitle] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [background, setBackground] = useState("technical");
  const [feedback, setFeedback] = useState({ text: "", type: "" });
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();

    if (!projectTitle.trim() || !projectDescription.trim()) {
      setFeedback({ text: "Project title and description are both required.", type: "error" });
      return;
    }

    setSaving(true);
    setFeedback({ text: "Saving project and owner membership...", type: "status" });

    setUserBackground(DEFAULT_USER_ID, background);

    try {
      const data = await createProjectRequest({
        user_id: DEFAULT_USER_ID,
        project_title: projectTitle.trim(),
        project_description: projectDescription.trim(),
        background: background,
      });

      setActiveProject(data);
      setFeedback({ text: "Project saved successfully. Opening requirement gathering...", type: "status" });
      navigate(`/requirement-agent?project_id=${encodeURIComponent(data.project_id)}`);
    } catch (error) {
      setFeedback({ text: error.message || "Unable to create the project.", type: "error" });
      setSaving(false);
    }
  }

  return (
    <div className="shell narrow" style={{ paddingTop: "48px" }}>
      <section className="card">
        <h1 className="page-title">Project details</h1>
        <p className="intro">
          Add the project title and description.
        </p>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label className="field-label">
            Project Title
            <input
              className="text-input"
              type="text"
              placeholder="Enter project title"
              value={projectTitle}
              onChange={(e) => setProjectTitle(e.target.value)}
            />
          </label>

          <label className="field-label">
            Project Description
            <textarea
              className="text-area"
              placeholder="Enter project description"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
            />
          </label>

          <fieldset className="background-field">
            <legend>Your Background</legend>
            <div className="background-options">
              <label>
                <input
                  type="radio"
                  name="bg"
                  value="technical"
                  checked={background === "technical"}
                  onChange={() => setBackground("technical")}
                />
                Technical
              </label>
              <label>
                <input
                  type="radio"
                  name="bg"
                  value="non_technical"
                  checked={background === "non_technical"}
                  onChange={() => setBackground("non_technical")}
                />
                Non-Technical
              </label>
            </div>
          </fieldset>


          <div className="actions-row">
            <Link className="ghost-btn" to="/add-project">Back</Link>
            <button className="secondary-btn" type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save Details"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
