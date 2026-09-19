import ScoreMeter from '../components/ScoreMeter.jsx'
import SpectralViewer from '../components/SpectralViewer.jsx'
import { ChangeTable, ChangeTrend, RegionImages } from '../components/ChangeView.jsx'
import { Note, Section, Tag } from '../components/Primitives.jsx'
import { DIRECTION_TEXT, TONE, TREND_TEXT, formatChange, formatDate, headline } from '../lib/analysis.js'

export function trendPoints(view, scan) {
  return [
    ...(view.history || []).map((point) => ({
      scan_number: point.scan_number, date: point.timestamp, change_percent: point.change_percent, is_current: false,
    })),
    { scan_number: view.scanNumber, date: scan?.timestamp, change_percent: view.changePercent, is_current: true },
  ]
}

export default function ResultScreen({ view, scan, photo, go }) {
  const verdict = headline(view)
  const isBaseline = view.stage === 'baseline'
  const baselineDate = view.history?.[0]?.timestamp

  return (
    <div className="stack">
      <section className="report-hero">
        <p className="eyebrow">
          {view.scanNumber ? `Scan ${view.scanNumber}` : 'Your observation'} · {formatDate(scan?.timestamp)}
        </p>
        <h1>{verdict.title}</h1>
        <p className="lede">{verdict.body}</p>
        <div className="row">
          <Tag tone={TONE[view.statusLabel] || 'steady'}>{view.statusLabel}</Tag>
          {!isBaseline && baselineDate ? <span className="caption">Compared with your baseline from {formatDate(baselineDate)}</span> : null}
        </div>
      </section>

      {isBaseline ? (
        <Section title="Your personal baseline">
          <p>
            Everyone’s skin is different, so SpectraDerm compares you with yourself. This scan is now your reference
            point.
          </p>
          <ul className="guidance">
            <li>Scan 2 will show the first change from this baseline.</li>
            <li>From scan 3 you will also see whether change is increasing, decreasing or stable.</li>
          </ul>
        </Section>
      ) : (
        <Section title="Change from your baseline">
          <div className="stat-row">
            <div className="stat">
              <span className="stat__value">{formatChange(view.changePercent)}</span>
              <span className="stat__label">overall change</span>
            </div>
            <div className="stat">
              <span className="stat__value">{DIRECTION_TEXT[view.direction] || '—'}</span>
              <span className="stat__label">since your previous scan</span>
            </div>
            <div className="stat">
              <span className="stat__value">{view.trend ? TREND_TEXT[view.trend] : 'From scan 3'}</span>
              <span className="stat__label">trend</span>
            </div>
          </div>
          {view.trendText ? <p>{view.trendText}</p> : null}
          {typeof view.changeScore === 'number' ? (
            <>
              <h3 className="subhead">Change score</h3>
              <ScoreMeter score={view.changeScore} />
              <p className="caption">This score shows how far this scan is from your own baseline. It is not a disease probability or a diagnosis.</p>
            </>
          ) : null}
        </Section>
      )}

      {!isBaseline && view.parameters.length ? (
        <Section title="What changed">
          <ChangeTable parameters={view.parameters} limit={4} showValues={false} />
          <p className="caption">The largest changes are shown. The full report lists every measured parameter.</p>
        </Section>
      ) : null}

      {view.visuals ? (
        <Section title={isBaseline ? 'Monitored region' : 'Where it changed'}>
          <RegionImages visuals={view.visuals} />
          {!isBaseline ? <p className="caption">The difference map assumes both photos were taken with similar framing and light.</p> : null}
        </Section>
      ) : null}

      {!isBaseline && (view.history?.length || 0) >= 1 ? (
        <Section title="Your history">
          <ChangeTrend points={trendPoints(view, scan)} />
        </Section>
      ) : null}

      <Section title="AI-estimated spectral view">
        <SpectralViewer spectral={view.spectral} photo={photo} unavailableReason={view.spectralUnavailableReason} />
      </Section>

      {view.quality?.passed === false && view.quality?.reasons?.length ? (
        <Note tone="observed">
          Photo quality was borderline: {view.quality.reasons.join(' ').toLowerCase()} Results may be less reliable.
        </Note>
      ) : null}

      <Section title={isBaseline ? 'About this scan' : 'Why was this flagged?'}>
        <p>{view.explanation ? firstParagraph(view.explanation) : 'Supporting information is not available for this scan.'}</p>
        <button type="button" className="btn btn--quiet" onClick={() => go('explanation')}>
          Read the explanation and sources
        </button>
      </Section>

      <section className="verdict" data-tone={view.referralRecommended ? 'notice' : 'steady'}>
        <h2>{view.referralRecommended ? 'Consider a professional assessment' : isBaseline ? 'Take your next scan in 2–4 weeks' : 'Continue monitoring'}</h2>
        <p className="lede">
          {view.referralRecommended
            ? 'The change has persisted across your scans. A dermatologist can examine what a photo cannot.'
            : 'Use similar light, distance and angle each time so your scans stay comparable.'}
        </p>
        <div className="row">
          <button type="button" className="btn btn--primary" onClick={() => go('report')}>View full report</button>
          <button type="button" className="btn btn--ghost" onClick={() => go(view.referralRecommended ? 'referral' : 'products')}>
            {view.referralRecommended ? 'Find a dermatologist' : 'General skincare'}
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => go('history')}>History</button>
        </div>
      </section>

      <Note>SpectraDerm monitors change over time. It does not diagnose skin conditions.</Note>
    </div>
  )
}

function firstParagraph(text) {
  const paragraph = text.split(/\n\s*\n/)[0].replace(/^What was observed:\s*/i, '')
  return paragraph.length > 320 ? `${paragraph.slice(0, 317)}…` : paragraph
}
