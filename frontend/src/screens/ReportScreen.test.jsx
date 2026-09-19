import { render, screen, within } from '@testing-library/react'
import { Report } from './ReportScreen.jsx'
import fixture from '../test/report.fixture.json'

describe('monitoring report', () => {
  it('renders all nine sections from a real backend report', () => {
    render(<Report report={fixture} go={vi.fn()} />)
    for (const title of ['Overall result', 'Detected change', 'Affected region', 'AI-estimated spectral analysis',
      'Historical comparison', 'Why was this flagged?', 'Safety assessment', 'Recommended next action', 'Technical details']) {
      expect(screen.getByRole('heading', { name: new RegExp(title.replace('?', '\?')) })).toBeInTheDocument()
    }
    expect(screen.getByText(fixture.scan.display_id)).toBeInTheDocument()
    expect(screen.getByText(/not a disease probability/i)).toBeInTheDocument()
    expect(screen.getByText(/does not diagnose skin diseases/i)).toBeInTheDocument()
  })

  it('lists every scan in the history table with the baseline first', () => {
    render(<Report report={fixture} go={vi.fn()} />)
    const tables = screen.getAllByRole('table')
    const history = tables[tables.length - 1]
    const rows = within(history).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(fixture.history.points.length)
    expect(within(rows[0]).getByText('Baseline')).toBeInTheDocument()
  })
})
