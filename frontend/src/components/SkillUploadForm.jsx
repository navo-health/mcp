import { useState } from "react";

const NAME_PATTERN = /^[a-z0-9_-]+$/;

export default function SkillUploadForm({ onCreate }) {
  const [name, setName] = useState("");
  const [skillMdFile, setSkillMdFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const nameValid = NAME_PATTERN.test(name);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!nameValid || !skillMdFile) return;

    setSubmitting(true);
    try {
      const description = await skillMdFile.text();

      await onCreate({ name, description });

      setName("");
      setSkillMdFile(null);
      e.target.reset();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card upload-form" onSubmit={handleSubmit}>
      <div className="form-title">Upload Skill</div>

      <div className="form-fields">
        <div>
          <label htmlFor="skill-name">Skill Name</label>
          <input
            id="skill-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="my_skill"
            required
          />
          {name && !nameValid ? (
            <span className="field-error">
              Lowercase letters, numbers, underscores, and hyphens only
            </span>
          ) : name ? null : (
            <span className="field-hint">lowercase, numbers, _ and - only</span>
          )}
        </div>

        <div>
          <label>Skill File (.md)</label>
          <div className="file-input-wrapper">
            <input
              type="file"
              accept=".md"
              required
              onChange={(e) => setSkillMdFile(e.target.files[0] || null)}
            />
          </div>
        </div>
      </div>

      <button
        type="submit"
        className="submit-btn"
        disabled={submitting || !nameValid || !skillMdFile}
      >
        {submitting ? "Uploading..." : "Upload Skill"}
      </button>
    </form>
  );
}
