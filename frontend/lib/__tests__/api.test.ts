const API = 'http://localhost:8000'

beforeEach(() => {
  global.fetch = jest.fn()
})

afterEach(() => {
  jest.resetAllMocks()
})

function mockFetch(body: unknown, status = 200) {
  ;(global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: status < 400,
    status,
    text: async () => JSON.stringify(body),
  })
}

describe('login', () => {
  it('posts credentials and returns user', async () => {
    mockFetch({ username: 'admin', is_admin: true })
    const { login } = await import('../api')
    const result = await login('admin', 'pass')
    expect(result).toEqual({ username: 'admin', is_admin: true })
    expect(global.fetch).toHaveBeenCalledWith(
      `${API}/auth/login`,
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    )
  })

  it('throws on 401', async () => {
    mockFetch({ error: 'Invalid credentials' }, 401)
    const { login } = await import('../api')
    await expect(login('bad', 'bad')).rejects.toThrow('Invalid credentials')
  })
})

describe('analyze', () => {
  it('returns task_id', async () => {
    mockFetch({ task_id: 'abc-123' }, 202)
    const { analyze } = await import('../api')
    const result = await analyze({
      lat: 28.6, lon: 77.2, location_name: 'Delhi',
      env_weather_risk: 0, env_width_factor: 1, env_event_active: false,
    })
    expect(result.task_id).toBe('abc-123')
  })
})

describe('pollResult', () => {
  it('returns pending when not ready', async () => {
    mockFetch({ status: 'pending', task_id: 'xyz' })
    const { pollResult } = await import('../api')
    const result = await pollResult('xyz')
    expect(result.status).toBe('pending')
  })
})

describe('getHistory', () => {
  it('returns array', async () => {
    mockFetch([{ id: 1, state: 'Stable' }])
    const { getHistory } = await import('../api')
    const result = await getHistory()
    expect(Array.isArray(result)).toBe(true)
  })
})
