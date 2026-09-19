import { DIRECTION_TEXT, formatChange, formatShortDate, formatValue } from '../lib/analysis.js'

/** What changed, parameter by parameter, against the personal baseline. */
export function ChangeTable({ parameters, limit, showValues = true }) {
  const rows = [...(parameters || [])]
    .filter((item) => item.current !== null && item.current !== undefined)
    .sort((a, b) => Math.abs(b.change_percent ?? 0) - Math.abs(a.change_percent ?? 0))
    .slice(0, limit || undefined)
  if (!rows.length) return null
  return (
    <div className="change-table-wrap">
      <table className="change-table">
        <thead>
          <tr>
            <th scope="col">Parameter</th>
            {showValues ? <th scope="col">Baseline</th> : null}
            {showValues ? <th scope="col">Current</th> : null}
            <th scope="col">Change</th>
            <th scope="col">Direction</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={item.label}>
              <th scope="row">{item.label}</th>
              {showValues ? <td>{formatValue(item.baseline)}</td> : null}
              {showValues ? <td>{formatValue(item.current)}</td> : null}
              <td>{formatChange(item.change_percent)}</td>
              <td data-direction={item.direction}>{DIRECTION_TEXT[item.direction] || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Baseline photo, current photo with the monitored region, and the difference map. */
export function RegionImages({ visuals, spectralHighlighted = false }) {
  if (!visuals) return null
  const panels = [
    visuals.baseline_image && { src: visuals.baseline_image, caption: 'Baseline (scan 1)' },
    visuals.current_highlighted && { src: visuals.current_highlighted, caption: 'Current scan · monitored region' },
    visuals.difference_map && { src: visuals.difference_map, caption: 'Difference map · brighter = more change' },
    spectralHighlighted && visuals.spectral_highlighted && {
      src: visuals.spectral_highlighted, caption: 'AI-estimated spectral view · same region',
    },
  ].filter(Boolean)
  if (!panels.length) return null
  return (
    <div className="image-grid">
      {panels.map((panel) => (
        <figure key={panel.caption}>
          <div className="frame frame--square">
            <img src={panel.src} alt={panel.caption} />
          </div>
          <figcaption className="caption">{panel.caption}</figcaption>
        </figure>
      ))}
    </div>
  )
}

/** Change from baseline across scans; the baseline itself sits at 0%. */
export function ChangeTrend({ points }) {
  const data = (points || []).map((point, index) => ({
    ...point,
    value: index === 0 ? 0 : typeof point.change_percent === 'number' ? point.change_percent : null,
  }))
  const scored = data.filter((point) => point.value !== null)
  if (scored.length < 2) {
    return <p className="muted">The trend chart appears once you have at least two scans.</p>
  }
  const width = 640
  const height = 220
  const pad = { top: 18, right: 18, bottom: 36, left: 44 }
  const top = Math.max(20, Math.ceil((Math.max(...scored.map((p) => p.value)) * 1.2) / 5) * 5)
  const x = (index) => pad.left + (index / (scored.length - 1)) * (width - pad.left - pad.right)
  const y = (value) => pad.top + (1 - value / top) * (height - pad.top - pad.bottom)
  const line = scored.map((point, index) => `${index ? 'L' : 'M'}${x(index)} ${y(point.value)}`).join(' ')
  const ticks = [0, top / 2, top]
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Change from baseline across ${scored.length} scans`}>
      {ticks.map((tick) => (
        <g key={tick}>
          <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} stroke="var(--hairline)" strokeDasharray={tick === 0 ? '0' : '3 4'} />
          <text x={4} y={y(tick) + 4} fontSize="11" fill="var(--taupe)">{`${tick.toFixed(0)}%`}</text>
        </g>
      ))}
      <path d={line} fill="none" stroke="var(--clay)" strokeWidth="2" strokeLinejoin="round" />
      {scored.map((point, index) => (
        <g key={`${point.scan_number}-${index}`}>
          <circle cx={x(index)} cy={y(point.value)} r={point.is_current ? 5 : 3.5} fill={point.is_current ? 'var(--clay)' : 'var(--ivory)'} stroke="var(--clay)" strokeWidth="1.5" />
          <text x={x(index)} y={height - 20} fontSize="11" fill="var(--ink-soft)" textAnchor="middle">
            {index === 0 ? 'Baseline' : `Scan ${point.scan_number}`}
          </text>
          <text x={x(index)} y={height - 6} fontSize="10" fill="var(--taupe)" textAnchor="middle">
            {formatShortDate(point.date)}
          </text>
        </g>
      ))}
    </svg>
  )
}
