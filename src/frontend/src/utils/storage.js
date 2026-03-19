export function setActiveProject(project) {
  sessionStorage.setItem("active_project_id", project.project_id);
  sessionStorage.setItem("active_project_title", project.project_title || "");
  sessionStorage.setItem("active_project_description", project.project_description || "");
}

export function getActiveProject() {
  return {
    project_id: sessionStorage.getItem("active_project_id"),
    project_title: sessionStorage.getItem("active_project_title") || "",
    project_description: sessionStorage.getItem("active_project_description") || "",
  };
}

export function setUserBackground(userId, background) {
  localStorage.setItem(`bg_${userId}`, background);
}

export function getUserBackground(userId) {
  return localStorage.getItem(`bg_${userId}`);
}
