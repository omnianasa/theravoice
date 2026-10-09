import React from "react";

export function Panel({ title, eyebrow, action, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || eyebrow || action) && (
        <div className="panel-heading">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && <h2>{title}</h2>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function StateMessage({ kind = "empty", title, children, action }) {
  return (
    <div className={`state-message state-${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span className="state-mark" aria-hidden="true">{kind === "error" ? "!" : kind === "loading" ? "…" : "i"}</span>
      <div>
        {title && <strong>{title}</strong>}
        {children && <p>{children}</p>}
        {action}
      </div>
    </div>
  );
}

export function Field({ label, hint, ...props }) {
  const id = props.id || props.name;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {props.type === "checkbox" ? (
        <div className="checkbox-field">
          <input id={id} {...props} />
          {hint && <span>{hint}</span>}
        </div>
      ) : (
        <>
          <input id={id} {...props} />
          {hint && <small>{hint}</small>}
        </>
      )}
    </div>
  );
}

export function ErrorNotice({ error, onRetry }) {
  if (!error) return null;
  return (
    <StateMessage kind="error" title="Something went wrong">
      {error.message || String(error)}
      {onRetry && <button className="button button-quiet" onClick={onRetry} type="button">Try again</button>}
    </StateMessage>
  );
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function Value({ value, available = true, reason }) {
  if (!available || value === null || value === undefined) {
    return <span className="unavailable-value">{reason ? `${reason} (unavailable)` : "Not available"}</span>;
  }
  return <span>{String(value)}</span>;
}
