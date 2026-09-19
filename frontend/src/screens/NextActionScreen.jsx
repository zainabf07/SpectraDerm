import { Note, PageHead, Section } from '../components/Primitives.jsx'

/**
 * The review step decides the path; this screen presents it. The
 * professional_assessment_recommended flag is the single gate, and the backend
 * closes whichever path does not apply.
 */
export default function NextActionScreen({ view, go }) {
  const safety = view.safety || {}
  const professional = view.referralRecommended

  return (
    <div className="stack">
      <PageHead
        back="Observation"
        onBack={() => go('result')}
        title={professional ? 'Consider professional evaluation' : 'Continue observing'}
        lede={
          professional
            ? 'Taken together with your earlier observations, this is worth showing to someone qualified to examine skin directly.'
            : 'Continue monitoring over time based on the available result.'
        }
      />

      <section className="verdict" data-tone={professional ? 'notice' : 'steady'}>
        <h2>{professional ? 'A clinician can examine what this cannot' : 'Observe again in about a month'}</h2>
        <p className="lede">
          {professional
            ? 'SpectraDerm cannot determine what is behind the difference it measured. Direct examination can.'
            : 'Regular photographs under similar conditions are what make the comparison useful. Three to five weeks suits most people.'}
        </p>
        <div className="row" style={{ marginTop: 'var(--s-5)' }}>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => go(professional ? 'referral' : 'products')}
          >
            {professional ? 'Find a dermatologist' : 'General skincare information'}
          </button>
        </div>
      </section>

      <Section>
        <Note>
          This is not a diagnosis. SpectraDerm records change over time.
        </Note>
      </Section>

      <Section>
        <div className="row">
          <button type="button" className="btn btn--ghost" onClick={() => go('history')}>
            My record
          </button>
        </div>
      </Section>
    </div>
  )
}
