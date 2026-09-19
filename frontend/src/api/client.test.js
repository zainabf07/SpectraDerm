import { api, ApiError } from './client.js'

describe('api client', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('normalizes API errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'X', message: 'Safe message' } }), { status: 404 })))
    await expect(api.getUser('u')).rejects.toMatchObject({ code: 'X', status: 404, message: 'Safe message' })
  })

  it('normalizes a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(api.getUser('u')).rejects.toBeInstanceOf(ApiError)
  })

  it('uploads multipart data without forcing a JSON content type', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ image_reference: 'images/u/x.jpg' }), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    await api.uploadImage('u', new File(['bytes'], 'a.jpg', { type: 'image/jpeg' }))
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/api/v1/users/u/image-artifacts')
    expect(init.body).toBeInstanceOf(FormData)
    expect(init.headers).toBeUndefined()
  })

  it('sends user_id as a query parameter for scan routes', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'completed', result: {} }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await api.analyze('s1', 'u1')
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/v1/scans/s1/analyze?user_id=u1')
  })
})
