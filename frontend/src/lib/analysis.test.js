import { formatChange, headline, qualityRejected, readResult } from './analysis.js'

const payload = (quality, overall = 'no_actionable_change') => ({
  status: 'completed',
  result: { vision_result: { overall_status: overall }, metadata: { pipeline: { quality } } },
})

describe('quality gate', () => {
  it('continues on a borderline REVIEW and stops only on REJECT', () => {
    expect(qualityRejected(readResult(payload({ status: 'REVIEW', passed: false })))).toBe(false)
    expect(qualityRejected(readResult(payload({ status: 'REJECT', passed: false })))).toBe(true)
    expect(qualityRejected(readResult(payload({ status: 'GOOD', passed: true }, 'insufficient_quality')))).toBe(true)
  })
})

describe('longitudinal progress', () => {
  it('reads baseline, change and trend from the pipeline progress', () => {
    const view = readResult({ result: { metadata: { pipeline: { progress: {
      stage: 'trend', scan_number: 3, status_label: 'Change detected', change_percent: 18.2, change_score: 70,
      direction_vs_previous: 'increased', trend: 'increasing', trend_text: 'Change is increasing.', parameters: [], history: [],
    } } } } })
    expect(view.scanNumber).toBe(3)
    expect(view.trend).toBe('increasing')
    expect(headline(view).title).toMatch(/change detected/i)
    expect(formatChange(view.changePercent)).toBe('+18.2%')
  })

  it('treats the first scan as the baseline', () => {
    const view = readResult({ result: { metadata: { pipeline: { progress: { stage: 'baseline', scan_number: 1, status_label: 'Baseline established' } } } } })
    expect(headline(view).title).toBe('Baseline established')
  })
})
