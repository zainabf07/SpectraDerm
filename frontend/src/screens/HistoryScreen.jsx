import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { store } from '../lib/store.js'
import { TONE, TREND_TEXT, formatChange, formatDate } from '../lib/analysis.js'
import { ChangeTrend } from '../components/ChangeView.jsx'
import { BackLink, Empty, Note, Section, Spinner, Tag } from '../components/Primitives.jsx'

export default function HistoryScreen({ userId, go, onOpenScan }) {
  const [state, setState] = useState({ phase: 'loading' })
  useEffect(() => {
    let live = true
    api
      .history(userId)
      .then((data) => {
        if (!live) return
        const cache = store.getScanCache()
        setState({ phase: 'done', timeline: (data.timeline || []).map((scan) => ({ ...scan, thumbnail: cache[scan.scan_id]?.thumbnail || null })) })
      })
      .catch((error) => live && setState({ phase: 'error', message: error.message }))
    return () => {
      live = false
    }
  }, [userId])

  if (state.phase === 'loading') return <Spinner label="Loading your history" />
  if (state.phase === 'error') return <Note tone="problem">{state.message}</Note>
  const timeline = state.timeline
  if (!timeline.length) {
    return (
      <div className="stack">
        <BackLink onClick={() => go('home')}>Home</BackLink>
        <Empty
          title="Your history starts here"
          body="Your first scan becomes your personal baseline. Every later scan is compared with it."
          action={<button type="button" className="btn btn--primary" onClick={() => go('scan')}>Start a scan</button>}
        />
      </div>
    )
  }
  const latest = timeline[timeline.length - 1]
  const points = timeline.map((scan, index) => ({
    scan_number: scan.scan_number ?? index + 1, date: scan.timestamp,
    change_percent: scan.change_percent, is_current: index === timeline.length - 1,
  }))

  return (
    <div className="stack">
      <div className="pagehead">
        <BackLink onClick={() => go('home')}>Home</BackLink>
        <div className="spread">
          <h1 style={{ fontSize: 'var(--step-4)' }}>Your skin history</h1>
          <button type="button" className="btn btn--primary" onClick={() => go('scan')}>Start a scan</button>
        </div>
      </div>

      <Section title={`${timeline.length} ${timeline.length === 1 ? 'scan' : 'scans'} recorded`}>
        {timeline.length === 1 ? (
          <p>Your baseline is established. Your next scan will show the first change from it.</p>
        ) : (
          <>
            <ChangeTrend points={points} />
            <p>
              Latest: <strong>{latest.status_label || 'Recorded'}</strong>
              {typeof latest.change_percent === 'number' ? ` · ${formatChange(latest.change_percent)} from baseline` : ''}
              {latest.trend ? ` · trend ${TREND_TEXT[latest.trend].toLowerCase()}` : timeline.length === 2 ? ' · trend available from your 3rd scan' : ''}
            </p>
          </>
        )}
      </Section>

      <Section title="Your scans">
        <ul className="entries">
          {[...timeline].reverse().map((scan, index) => {
            const number = scan.scan_number ?? timeline.length - index
            return (
              <li key={scan.scan_id}>
                <button type="button" className="entry" onClick={() => onOpenScan(scan)}>
                  {scan.thumbnail ? <img className="entry__thumb" src={scan.thumbnail} alt="" /> : <span className="entry__thumb" aria-hidden="true" />}
                  <span className="entry__body">
                    <span className="entry__title">{number === 1 ? 'Baseline' : `Scan ${number}`} · {formatDate(scan.timestamp)}</span>
                    <span className="entry__meta">
                      <Tag tone={TONE[scan.status_label] || 'steady'}>{scan.status_label || 'Recorded'}</Tag>
                      {typeof scan.change_percent === 'number' ? ` ${formatChange(scan.change_percent)} from baseline` : ''}
                    </span>
                  </span>
                  <span className="entry__open">Open</span>
                </button>
              </li>
            )
          })}
        </ul>
      </Section>
    </div>
  )
}
