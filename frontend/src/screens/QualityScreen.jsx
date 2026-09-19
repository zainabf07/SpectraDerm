import { qualityReasons } from '../lib/analysis.js'
import { PageHead, Section } from '../components/Primitives.jsx'

/** The photograph check runs before comparison, so no score is offered here. */
export default function QualityScreen({ view, photo, go }) {
  const reasons = qualityReasons(view)

  return (
    <div className="stack">
      <PageHead
        title="This photograph needs retaking"
        lede="It did not meet the conditions needed for a reliable comparison, so SpectraDerm stopped before comparing it. The observation is stored, but it will not be used as a reference."
      />

      <Section>
        <div className="pair">
          <div>
            <div className="frame">{photo ? <img src={photo} alt="The photograph taken" /> : null}</div>
            <p className="caption">The photograph you took</p>
          </div>
          <div>
            <h3 style={{ marginBottom: 'var(--s-4)' }}>What stood in the way</h3>
            {reasons.length ? (
              <ul className="guidance">
                {reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">
                The check did not meet its conditions without naming a specific measurement.
              </p>
            )}
          </div>
        </div>
      </Section>

      <Section title="Before you retake it">
        <ul className="guidance">
          <li>Move to brighter, even light and turn the flash off.</li>
          <li>Hold still, tap to focus on the area, then take the photograph.</li>
          <li>Fill more of the frame with skin and less with background.</li>
        </ul>
      </Section>

      <div className="row">
        <button type="button" className="btn btn--primary" onClick={() => go('scan')}>
          Retake the photograph
        </button>
        <button type="button" className="btn btn--ghost" onClick={() => go('history')}>
          Back to my record
        </button>
      </div>
    </div>
  )
}
