import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { store } from '../lib/store.js'
import { formatDate } from '../lib/analysis.js'
import { Note, Section } from '../components/Primitives.jsx'

export default function HomeScreen({ userId, go }) {
  const [scans, setScans] = useState(null)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    let live = true
    if (!userId) {
      setScans([])
      return undefined
    }
    api
      .listScans(userId)
      .then((data) => live && setScans(data.scans || []))
      .catch(() => live && setUnreachable(true))
    return () => {
      live = false
    }
  }, [userId])

  const latest = scans && scans.length ? scans[scans.length - 1] : null
  const cached = latest ? store.getScanEntry(latest.scan_id) : null

  return (
    <div className="stack">
      <div className="hero">
        <div className="hero__rule" />
        <h1>Notice what changes, before you would notice it yourself.</h1>
        <p className="lede">
          SpectraDerm compares each photograph with the ones you took before, and tells you when
          something looks different. It observes. It does not diagnose.
        </p>
        <div className="hero__actions">
          <button type="button" className="btn btn--primary" onClick={() => go('scan')}>
            Take an observation
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => go('history')}>
            View my record
          </button>
        </div>

        <div className="factline">
          <div>
            <span className="fact__value">{scans ? scans.length : '—'}</span>
            <span className="fact__label">observations recorded</span>
          </div>
          <div>
            <span className="fact__value">{latest ? formatDate(latest.timestamp) : 'None yet'}</span>
            <span className="fact__label">most recent</span>
          </div>
          <div>
            <span className="fact__value">
              {cached?.statusLabel || (scans && scans.length ? 'Recorded' : 'Not started')}
            </span>
            <span className="fact__label">current state</span>
          </div>
        </div>
      </div>

      {unreachable ? (
        <Note tone="problem">
          The SpectraDerm service is not responding. Start it with{' '}
          <code>uvicorn spectraderm.api.app:app --reload</code>, then reload this page.
        </Note>
      ) : null}

      <Section title="How an observation works">
        <ol className="sequence">
          <li>You photograph the area you want to keep an eye on.</li>
          <li>SpectraDerm checks the photograph is clear enough to compare.</li>
          <li>Detail beyond what the camera records is estimated from the image.</li>
          <li>That estimate is compared with the baseline built from your earlier photographs.</li>
          <li>You see what differed, the information behind it, and a suggested next step.</li>
        </ol>
      </Section>

      <Section>
        <Note>
          SpectraDerm supports observation over time. It is not a medical device and cannot tell you
          what a change means. Anything persistent or worrying is worth raising with a clinician.
        </Note>
      </Section>
    </div>
  )
}
