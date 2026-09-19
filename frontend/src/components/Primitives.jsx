/**
 * The shared primitives. Every screen composes these so button, section, tag
 * and note language stays identical across the product.
 */

/** An editorial section: a hairline, a title, then content. Not a card. */
export function Section({ title, action, children }) {
  return (
    <section className="section">
      {(title || action) && (
        <div className="section__head">
          {title ? <h3>{title}</h3> : <span />}
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

/**
 * A raised surface. Used sparingly — a clinic listing, a single image — where
 * the content genuinely needs to sit apart from the page.
 */
export function Tile({ children }) {
  return <div className="tile">{children}</div>
}

/** Tone is one of: steady, observed, notice. Never an alarm colour. */
export function Tag({ tone = 'steady', children }) {
  return (
    <span className="tag" data-tone={tone}>
      {children}
    </span>
  )
}

export function Note({ tone = 'plain', children }) {
  const cls =
    tone === 'observed' ? 'note note--observed' : tone === 'problem' ? 'note note--problem' : 'note'
  return <div className={cls}>{children}</div>
}

export function BackLink({ onClick, children }) {
  return (
    <button type="button" className="backlink" onClick={onClick}>
      ← {children}
    </button>
  )
}

export function PageHead({ back, onBack, title, lede }) {
  return (
    <div className="pagehead">
      {back ? <BackLink onClick={onBack}>{back}</BackLink> : null}
      <h1>{title}</h1>
      {lede ? <p className="lede">{lede}</p> : null}
    </div>
  )
}

export function Spinner({ label }) {
  return (
    <span>
      <span className="spinner" aria-hidden="true" />
      {label ? <span className="muted"> {label}</span> : null}
      <span className="sr-only">Loading</span>
    </span>
  )
}

export function Empty({ title, body, action }) {
  return (
    <section className="section">
      <h2>{title}</h2>
      <p className="lede" style={{ marginTop: 'var(--s-4)' }}>
        {body}
      </p>
      {action ? <div className="row" style={{ marginTop: 'var(--s-5)' }}>{action}</div> : null}
    </section>
  )
}

/** Definition list used by the report and the detail panels. */
export function KeyValues({ items }) {
  const rows = items.filter((row) => row && row[1] !== null && row[1] !== undefined && row[1] !== '')
  if (!rows.length) return null
  return (
    <dl className="keyvalue">
      {rows.map(([label, value]) => (
        <div key={label} style={{ display: 'contents' }}>
          <dt>{label}</dt>
          <dd>{typeof value === 'string' || typeof value === 'number' ? value : JSON.stringify(value)}</dd>
        </div>
      ))}
    </dl>
  )
}
