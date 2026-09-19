import { useEffect, useState } from 'react'
import { Note } from '../components/Primitives.jsx'

const STAGES = [
  'Checking the photograph',
  'Locating skin in the frame',
  'Estimating spectral detail',
  'Measuring colour and texture',
  'Comparing with your baseline',
  'Gathering supporting information',
]

/**
 * Analysis is a single blocking call, so this screen paces the stage list
 * rather than polling. The last stage never completes on its own — it clears
 * when the real response arrives.
 */
export default function AnalyzingScreen({ photo, error, onRetry, go }) {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    if (error) return undefined
    const timer = setInterval(() => {
      setStage((current) => (current < STAGES.length - 1 ? current + 1 : current))
    }, 1400)
    return () => clearInterval(timer)
  }, [error])

  if (error) {
    return (
      <div className="stack">
        <h1>Comparison stopped</h1>
        <Note tone="problem">{error.message}</Note>
        <div className="row">
          <button type="button" className="btn btn--primary" onClick={onRetry}>
            Try again
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => go('scan')}>
            Use another photograph
          </button>
        </div>
      </div>
    )
  }

  const progress = Math.round(((stage + 0.5) / STAGES.length) * 100)

  return (
    <div className="stack">
      <div className="pagehead">
        <h1>Comparing</h1>
        <p className="lede">This takes a few seconds. Leaving this page cancels it.</p>
      </div>

      <section className="section">
        <div className="pair">
          <div>
            <div className="frame">
              {photo ? <img src={photo} alt="The photograph being compared" /> : null}
            </div>
            <p className="caption">Your photograph</p>
          </div>
          <div>
            <div className="frame frame--empty">
              <span>Estimated spectral view appears here</span>
            </div>
            <p className="caption">Estimated spectral information</p>
          </div>
        </div>

        <ol className="pipeline" style={{ marginTop: 'var(--s-6)' }}>
          {STAGES.map((label, index) => (
            <li
              key={label}
              data-state={index < stage ? 'done' : index === stage ? 'active' : 'waiting'}
            >
              <span className="pipeline__dot" aria-hidden="true" />
              <span>{label}</span>
            </li>
          ))}
        </ol>

        <div className="progress">
          <div className="progress__fill" style={{ width: `${progress}%` }} />
        </div>
      </section>
    </div>
  )
}
