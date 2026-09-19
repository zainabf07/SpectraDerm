import { StrictMode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import App, { resetUserBootstrap } from './App.jsx'
import { api, ApiError } from './api/client.js'

vi.mock('./api/client.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    api: {
      createUser: vi.fn().mockResolvedValue({ user_id: 'fresh' }),
      getUser: vi.fn(),
      listScans: vi.fn().mockResolvedValue({ scans: [] }),
    },
  }
})

describe('session bootstrap', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    resetUserBootstrap()
  })

  it('keeps a user id the API still knows', async () => {
    localStorage.setItem('spectraderm.user_id', 'known')
    api.getUser.mockResolvedValueOnce({ user_id: 'known' })
    render(<App />)
    await waitFor(() => expect(api.listScans).toHaveBeenCalledWith('known'))
    expect(api.createUser).not.toHaveBeenCalled()
  })

  it('creates exactly one user under StrictMode double mounting', async () => {
    render(<StrictMode><App /></StrictMode>)
    await waitFor(() => expect(localStorage.getItem('spectraderm.user_id')).toBe('fresh'))
    expect(api.createUser).toHaveBeenCalledTimes(1)
  })

  it('replaces a stale user id the API has forgotten', async () => {
    localStorage.setItem('spectraderm.user_id', 'stale')
    api.getUser.mockRejectedValueOnce(new ApiError('USER_NOT_FOUND', 'User was not found.', 404))
    render(<App />)
    await waitFor(() => expect(localStorage.getItem('spectraderm.user_id')).toBe('fresh'))
    expect(api.listScans).toHaveBeenCalledWith('fresh')
  })

  it('reports an unreachable API instead of hanging', async () => {
    api.createUser.mockRejectedValueOnce(new ApiError('NETWORK_UNREACHABLE', 'The SpectraDerm service did not respond.', 0))
    render(<App />)
    expect(await screen.findByText(/could not reach the spectraderm service/i)).toBeInTheDocument()
  })
})
