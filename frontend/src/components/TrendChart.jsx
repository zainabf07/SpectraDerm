import { formatShortDate } from '../lib/analysis.js'

/** Change score over time. Points without a score are simply absent. */
export default function TrendChart({ points }) {
  const scored = points.filter((point) => typeof point.score === 'number' && Number.isFinite(point.score))

  if (scored.length < 2) {
    return (
      <p className="muted" style={{ margin: 0 }}>
        A model-derived change trend is not available yet.
      </p>
    )
  }

  const width = 640
  const height = 230
  const pad = { top: 18, right: 16, bottom: 34, left: 34 }
  const x = (index) => pad.left + (index / (scored.length - 1)) * (width - pad.left - pad.right)
  const y = (score) => pad.top + (1 - Math.max(0, Math.min(100, score)) / 100) * (height - pad.top - pad.bottom)

  const line = scored.map((point, index) => `${index ? 'L' : 'M'}${x(index)} ${y(point.score)}`).join(' ')

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Difference score across ${scored.length} scans`}
    >
      {[0, 25, 50, 75, 100].map((tick) => (
        <g key={tick}>
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={y(tick)}
            y2={y(tick)}
            stroke="var(--hairline)"
            strokeDasharray={tick === 0 ? '0' : '3 4'}
          />
          <text x={2} y={y(tick) + 4} fontSize="11" fill="var(--slate)">
            {tick}
          </text>
        </g>
      ))}

      <path d={line} fill="none" stroke="var(--ink)" strokeWidth="1.5" strokeLinejoin="round" />

      {scored.map((point, index) => (
        <g key={point.scanId}>
          <circle cx={x(index)} cy={y(point.score)} r="3.5" fill="var(--ivory)" stroke="var(--ink)" strokeWidth="1.5" />
          <text x={x(index)} y={height - 12} fontSize="11" fill="var(--slate)" textAnchor="middle">
            {formatShortDate(point.timestamp)}
          </text>
        </g>
      ))}
    </svg>
  )
}
