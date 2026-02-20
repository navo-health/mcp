export default function SkillList({ skills, onDelete }) {
  if (skills.length === 0) {
    return <p className="empty-state">No skills installed yet. Upload one above to get started.</p>;
  }

  return (
    <ul className="skill-list">
      {skills.map((skill) => (
        <li key={skill.name} className="skill-item">
          <div className="skill-info">
            <span className="skill-name">{skill.name}</span>
            {skill.description && (
              <p className="skill-description">{skill.description}</p>
            )}
          </div>
          <button
            className="delete-btn"
            onClick={() => {
              if (window.confirm(`Delete skill "${skill.name}"?`)) {
                onDelete(skill.name);
              }
            }}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
