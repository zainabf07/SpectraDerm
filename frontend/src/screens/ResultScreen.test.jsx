import { render, screen } from '@testing-library/react'
import ResultScreen from './ResultScreen.jsx'
import ExplanationScreen from './ExplanationScreen.jsx'

const base = {
  stage: 'baseline', scanNumber: 1, statusLabel: 'Baseline established', changePercent: null, changeScore: null,
  direction: null, trend: null, trendText: null, parameters: [], history: [], visuals: null, spectral: null,
  spectralUnavailableReason: 'Not available', quality: { passed: true }, explanation: null, sources: [], referralRecommended: false,
}
const scan = { timestamp: '2026-09-18T00:00:00Z' }
const params = [
  { label: 'Redness-related feature', baseline: 1.1, current: 1.6, change_percent: 44.3, direction: 'increased' },
  { label: 'Brightness', baseline: 0.3, current: 0.24, change_percent: -24.1, direction: 'decreased' },
]

describe('result screen journey', () => {
  it('scan 1 establishes the baseline without a score or trend', () => {
    render(<ResultScreen view={base} scan={scan} photo={null} go={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Baseline established' })).toBeInTheDocument()
    expect(screen.getByText(/scan 2 will show the first change/i)).toBeInTheDocument()
    expect(screen.queryByText(/\/ 100/)).not.toBeInTheDocument()
  })

  it('scan 2 shows the first change and says the trend comes later', () => {
    const view = { ...base, stage: 'first_comparison', scanNumber: 2, statusLabel: 'Slight change', changePercent: 9.8, changeScore: 48,
      direction: 'increased', parameters: params, history: [{ scan_number: 1, timestamp: '2026-09-01T00:00:00Z', change_percent: null }] }
    render(<ResultScreen view={view} scan={scan} photo={null} go={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /slight change/i })).toBeInTheDocument()
    expect(screen.getByText('+9.8%')).toBeInTheDocument()
    expect(screen.getByText('From scan 3')).toBeInTheDocument()
    expect(screen.getByText('Redness-related feature')).toBeInTheDocument()
  })

  it('scan 3+ shows the trend and the referral path when safety recommends it', () => {
    const view = { ...base, stage: 'trend', scanNumber: 5, statusLabel: 'Change detected', changePercent: 21.3, changeScore: 75.8,
      direction: 'increased', trend: 'increasing', trendText: 'Change has increased across the last 4 comparisons.', parameters: params,
      history: [1, 2, 3, 4].map((n) => ({ scan_number: n, timestamp: `2026-0${n}-01T00:00:00Z`, change_percent: n === 1 ? null : n })),
      referralRecommended: true }
    const go = vi.fn()
    render(<ResultScreen view={view} scan={scan} photo={null} go={go} />)
    expect(screen.getByText('Increasing')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /change from baseline across 5 scans/i })).toBeInTheDocument()
    screen.getByRole('button', { name: 'Find a dermatologist' }).click()
    expect(go).toHaveBeenCalledWith('referral')
  })

  it('renders the explanation and its sources', () => {
    const explanation = 'What was observed: A change of 21%.\n\nWhy it can matter:\n- Irregular colour can have several causes. [NHS]\n\nThe observed change alone does not identify a specific condition; these sources give general context only.'
    render(<ExplanationScreen view={{ ...base, explanation, sources: [{ text: 'Context.', source: { title: 'Source title', organization: 'NHS', url: 'https://example.test' } }] }} go={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Why it can matter' })).toBeInTheDocument()
    expect(screen.getByText(/summarised directly from the sources/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View source' })).toHaveAttribute('href', 'https://example.test')
  })
})
