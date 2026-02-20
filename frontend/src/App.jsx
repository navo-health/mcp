import { useState, useEffect, useCallback } from "react";
import SkillUploadForm from "./components/SkillUploadForm.jsx";
import SkillList from "./components/SkillList.jsx";

export default function App() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSkills = useCallback(async () => {
    try {
      const res = await fetch("/api/skills");
      if (!res.ok) throw new Error(`Failed to fetch skills (${res.status})`);
      const data = await res.json();
      setSkills(data.skills);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(null), 5000);
    return () => clearTimeout(timer);
  }, [error]);

  async function handleCreate({ name, description }) {
    const res = await fetch("/api/skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Upload failed (${res.status})`);
    }
    await fetchSkills();
  }

  async function handleDelete(name) {
    const res = await fetch(`/api/skills/${name}`, { method: "DELETE" });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(body.detail || `Delete failed (${res.status})`);
      return;
    }
    await fetchSkills();
  }

  return (
    <div className="container">
      <header className="page-header">
        <h1>Skills <span>Gateway</span></h1>
        <p className="page-subtitle">Manage agent skills</p>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <SkillUploadForm
        onCreate={async (payload) => {
          try {
            await handleCreate(payload);
          } catch (err) {
            setError(err.message);
          }
        }}
      />

      <div className="section-label">
        Installed Skills
        {!loading && <span className="skill-count">{skills.length}</span>}
      </div>
      {loading ? (
        <p className="loading">Loading</p>
      ) : (
        <SkillList skills={skills} onDelete={handleDelete} />
      )}
    </div>
  );
}
