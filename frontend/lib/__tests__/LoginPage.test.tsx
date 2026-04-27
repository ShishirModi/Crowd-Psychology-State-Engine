import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LoginPage from '@/app/login/page'

jest.mock('@/lib/api', () => ({
  login: jest.fn(),
}))

const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: { getItem: jest.fn(), setItem: jest.fn(), removeItem: jest.fn() },
      writable: true,
    })
  })

  it('renders username and password fields', () => {
    render(<LoginPage />)
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
  })

  it('redirects to /dashboard on success', async () => {
    const { login } = await import('@/lib/api')
    ;(login as jest.Mock).mockResolvedValueOnce({ username: 'admin', is_admin: true })
    render(<LoginPage />)
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'cpseisawesome' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/dashboard'))
  })

  it('shows error on 401', async () => {
    const { login } = await import('@/lib/api')
    ;(login as jest.Mock).mockRejectedValueOnce(new Error('Invalid credentials'))
    render(<LoginPage />)
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'bad' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'bad' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(screen.getByText('Invalid credentials')).toBeInTheDocument())
  })
})
