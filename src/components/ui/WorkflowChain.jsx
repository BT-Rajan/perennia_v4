import "./WorkflowChain.css";

/**
 * A connected sequence of workflow stages (e.g. Sales → … → Payment),
 * shown as one ordered list of plain labels joined by arrows. Wraps on
 * narrow screens. Used by the homepage case-study teaser and by the
 * Markdown `[[workflow: A → B → C]]` block on content pages, so both
 * show the same thing the same way.
 */
export default function WorkflowChain({ stages, label, className }) {
  if (!stages?.length) return null;
  return (
    <ol className={`workflow-chain ${className || ""}`.trim()} aria-label={label}>
      {stages.map((stage, i) => (
        <li key={i}>{stage}</li>
      ))}
    </ol>
  );
}
