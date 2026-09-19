import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { ChangeTable, ChangeTrend, RegionImages } from '../components/ChangeView.jsx'
import ScoreMeter from '../components/ScoreMeter.jsx'
import { BackLink, Note, Spinner, Tag } from '../components/Primitives.jsx'
import { ExplanationText, ORIGIN_TEXT } from './ExplanationScreen.jsx'
import { DIRECTION_TEXT, TONE, TREND_TEXT, formatChange, formatDate } from '../lib/analysis.js'

export default function ReportScreen({ scanId, userId, go }) {
  const [state, setState] = useState({ phase: 'loading' })

  useEffect(() => {
    let live = true
    api
      .monitoringReport(scanId, userId)
      .then((report) => live && setState({ phase: 'done', report }))
      .catch((error) => live && setState({ phase: 'error', message: error.message }))
    return () => {
      live = false
    }
  }, [scanId, userId])

  if (state.phase === 'loading') return <Spinner label="Preparing your report" />
  if (state.phase === 'error') return <Note tone="problem">{state.message}</Note>
  return <Report report={state.report} go={go} />
}

export function Report({ report, go }) {
  const { scan, overall, detected_change: change, region, spectral, history, explanation, safety, next_action: next, technical } = report
  const isBaseline = overall.stage === 'baseline'
  let number = 0
  const section = () => ++number

  return (
    <article className="report stack">
      <div className="pagehead no-print">
        <BackLink onClick={() => go('result')}>Result</BackLink>
      </div>

      <header className="report-header">
        <p className="eyebrow">SpectraDerm</p>
        <h1>Skin Monitoring Report</h1>
        <dl className="report-meta">
          <div><dt>Scan ID</dt><dd>{scan.display_id}</dd></div>
          <div><dt>Date</dt><dd>{formatDate(scan.date)}</dd></div>
          <div><dt>Reference</dt><dd>{scan.reference ? `${scan.reference.label} (${formatDate(scan.reference.date)})` : 'This scan is the personal baseline'}</dd></div>
        </dl>
        <div className="row no-print">
          <button type="button" className="btn btn--ghost" onClick={() => window.print()}>Print or save as PDF</button>
        </div>
      </header>

      <ReportSection number={section()} title="Overall result">
        <div className="verdict" data-tone={overall.tone === 'change' ? 'notice' : overall.tone === 'monitor' ? 'observed' : 'steady'}>
          <Tag tone={TONE[overall.status_label] || 'steady'}>{overall.status_label}</Tag>
          <h2>{overall.headline}</h2>
          <p className="lede">{overall.summary}</p>
        </div>
        {!isBaseline ? (
          <>
            <div className="stat-row">
              <div className="stat"><span className="stat__value">{formatChange(overall.change_percent)}</span><span className="stat__label">change from baseline</span></div>
              <div className="stat"><span className="stat__value">{DIRECTION_TEXT[overall.direction] || '—'}</span><span className="stat__label">since previous scan</span></div>
              <div className="stat"><span className="stat__value">{overall.trend ? TREND_TEXT[overall.trend] : 'From scan 3'}</span><span className="stat__label">trend</span></div>
              <div className="stat"><span className="stat__value">{overall.reliability.label}</span><span className="stat__label">analysis reliability</span></div>
            </div>
            <h3 className="subhead">Change / anomaly score</h3>
            <ScoreMeter score={overall.change_score} />
          </>
        ) : null}
        <Note tone="observed">{overall.score_note}</Note>
      </ReportSection>

      <ReportSection number={section()} title="Detected change">
        {change.available ? (
          <>
            <ChangeTable parameters={change.parameters} />
            <p className="caption">Values are model-derived measurements of the monitored region. They describe what changed, not what it means medically.</p>
          </>
        ) : (
          <p>No change yet — this scan is your baseline. Your next scan will be compared with it.</p>
        )}
      </ReportSection>

      <ReportSection number={section()} title="Affected region">
        <RegionImages visuals={region} spectralHighlighted />
        {region.difference_map ? <p className="caption">{region.note}</p> : null}
      </ReportSection>

      <ReportSection number={section()} title="AI-estimated spectral analysis">
        {spectral.available ? (
          <div className="image-grid">
            <figure><div className="frame frame--square"><img src={spectral.false_color_image} alt="AI-estimated spectral representation" /></div><figcaption className="caption">AI-estimated spectral representation</figcaption></figure>
            {spectral.band_image ? <figure><div className="frame frame--square"><img src={spectral.band_image} alt={`Estimated ${spectral.band_wavelength_nm} nm band`} /></div><figcaption className="caption">Estimated {spectral.band_wavelength_nm} nm band</figcaption></figure> : null}
          </div>
        ) : <p>AI-estimated spectral information was not available for this scan.</p>}
        <Note>{spectral.note}</Note>
      </ReportSection>

      <ReportSection number={section()} title="Historical comparison">
        <ChangeTrend points={history.points} />
        <div className="change-table-wrap">
          <table className="change-table">
            <thead><tr><th scope="col">Scan</th><th scope="col">Date</th><th scope="col">Status</th><th scope="col">Change</th></tr></thead>
            <tbody>
              {history.points.map((point) => (
                <tr key={`${point.scan_number}-${point.date}`} data-current={point.is_current || undefined}>
                  <th scope="row">{point.scan_number === 1 ? 'Baseline' : point.is_current ? `Current (scan ${point.scan_number})` : `Scan ${point.scan_number}`}</th>
                  <td>{formatDate(point.date)}</td>
                  <td>{point.status || '—'}</td>
                  <td>{point.scan_number === 1 ? '—' : formatChange(point.change_percent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {history.trend_text ? <p>{history.trend_text}</p> : null}
      </ReportSection>

      <ReportSection number={section()} title="Why was this flagged?">
        {explanation.text ? <ExplanationText text={explanation.text} /> : (
          <p>{explanation.withheld ? 'The explanation was withheld by the safety review. The sources are listed below.' : 'An explanation is not available for this scan.'}</p>
        )}
        {ORIGIN_TEXT[explanation.origin] ? <p className="caption">{ORIGIN_TEXT[explanation.origin]}</p> : null}
        {explanation.sources.length ? (
          <>
            <h3 className="subhead">Evidence — {explanation.evidence_count} relevant {explanation.evidence_count === 1 ? 'source' : 'sources'} retrieved</h3>
            <ol className="sources">
              {explanation.sources.map((source, index) => (
                <li key={`${source.url}-${index}`}>
                  <strong>{source.title}</strong> — {source.organization}
                  {source.url ? <> · <a href={source.url} target="_blank" rel="noreferrer">View source</a></> : null}
                </li>
              ))}
            </ol>
          </>
        ) : null}
      </ReportSection>

      <ReportSection number={section()} title="Safety assessment">
        <p><strong>Assessment:</strong> {safety.assessment}</p>
        {safety.notes.map((note) => <p key={note} className="muted">{note}</p>)}
      </ReportSection>

      <ReportSection number={section()} title="Recommended next action">
        <div className="verdict" data-tone={next.type === 'professional' ? 'notice' : 'steady'}>
          <h2>{next.title}</h2>
          <ul className="guidance">{next.steps.map((step) => <li key={step}>{step}</li>)}</ul>
          <div className="row no-print">
            {next.type === 'professional' ? (
              <button type="button" className="btn btn--primary" onClick={() => go('referral')}>Find a dermatologist</button>
            ) : (
              <button type="button" className="btn btn--primary" onClick={() => go('scan')}>Start a new scan</button>
            )}
            <button type="button" className="btn btn--ghost" onClick={() => go('history')}>History</button>
          </div>
        </div>
      </ReportSection>

      <ReportSection number={section()} title="Technical details">
        <details className="tech">
          <summary>Show technical analysis details</summary>
          <dl className="keyvalue">
            <dt>Image quality</dt><dd>{technical.image_quality.status === 'GOOD' ? 'Passed' : technical.image_quality.status === 'REVIEW' ? `Borderline — ${technical.image_quality.reasons.join(' ')}` : technical.image_quality.status || '—'}</dd>
            <dt>Skin region</dt><dd>{technical.skin_detected ? 'Detected' : 'Not detected'}</dd>
            <dt>Monitored region</dt><dd>{technical.monitored_region || '—'}</dd>
            <dt>RGB input</dt><dd>{shape(technical.rgb_input_shape)}</dd>
            <dt>Estimated spectral output</dt><dd>{shape(technical.spectral_output_shape)}</dd>
            <dt>Reconstruction status</dt><dd>{technical.reconstruction_status}</dd>
            <dt>Features analysed</dt><dd>{technical.features_used.join(' · ')}</dd>
            <dt>Change score method</dt><dd>{technical.change_score_method}</dd>
            <dt>Reference-variation model</dt><dd>{technical.anomaly_model?.available ? `${technical.anomaly_model.score.toFixed(0)} / 100 (${technical.anomaly_model.category})` : `Needs ${technical.anomaly_model?.minimum_reference_scans ?? 4} earlier scans`}</dd>
          </dl>
          <p className="caption">Spectral information is AI-estimated from the RGB photo; it is not a multispectral or hyperspectral measurement.</p>
        </details>
      </ReportSection>

      <footer className="report-disclaimer">
        <strong>Important:</strong> {report.disclaimer}
      </footer>
    </article>
  )
}

function ReportSection({ number, title, children }) {
  return (
    <section className="section report-section">
      <h2 className="report-section__title"><span>{number}.</span> {title}</h2>
      {children}
    </section>
  )
}

function shape(value) {
  return Array.isArray(value) && value.length ? value.join(' × ') : '—'
}
