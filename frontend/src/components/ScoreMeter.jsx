import { scoreBand } from '../lib/analysis.js'
import { Tag } from './Primitives.jsx'

/**
 * The difference score is a measure of distance from the person's own
 * baseline, not a probability. It is drawn as a position along a single line
 * rather than as a dial that fills up, so it never reads as a severity gauge.
 */
export default function ScoreMeter({ score, previous }) {
  if (score === null || score === undefined) {
    return (
      <div className="score">
        <div className="score__value">
          —<small> / 100</small>
        </div>
        <p className="muted">A change score is available from your second scan.</p>
      </div>
    )
  }

  const clamped = Math.max(0, Math.min(100, score))
  const band = scoreBand(clamped)
  const hasPrevious = typeof previous === 'number' && Number.isFinite(previous)

  return (
    <div className="score">
      <div className="spread">
        <div className="score__value">
          {clamped.toFixed(0)}
          <small> / 100</small>
        </div>
        <Tag tone={band.tone}>{band.label}</Tag>
      </div>

      <div
        className="score__track"
        role="img"
        aria-label={`Difference score ${clamped.toFixed(0)} out of 100`}
      >
        <div className="score__fill" style={{ width: `${clamped}%` }} />
        {hasPrevious ? (
          <div
            className="score__marker"
            style={{ left: `${Math.max(0, Math.min(100, previous))}%` }}
          />
        ) : null}
      </div>

      <div className="score__scale">
        <span>0 · matches your baseline</span>
        <span>100 · furthest from it</span>
      </div>

      {hasPrevious ? (
        <p className="muted">The short mark shows your previous observation at {previous.toFixed(0)}.</p>
      ) : null}
    </div>
  )
}
