import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInterface from './ChatInterface'
import { ProfileProvider } from '@/context/ProfileContext'

function renderWithProvider() {
  return render(
    <ProfileProvider>
      <ChatInterface apiEndpoint="/api/chat" title="Test" subtitle="Test" suggestions={[]} />
    </ProfileProvider>,
  )
}

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/profile')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                user_id: 'test-id',
                dietary_preference: 'No rules',
                allergens: [],
                lifestyle: [],
              }),
          })
        }
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ error: 'Chat failed', detail: 'Backend error' }),
        })
      }),
    )
  })

  it('shows empty state and displays error message when chat request fails', async () => {
    renderWithProvider()

    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Type ingredient/)
      expect(input).toBeInTheDocument()
      expect(input).not.toBeDisabled()
    })

    const input = screen.getByPlaceholderText(/Type ingredient/)
    await userEvent.type(input, 'Is this vegan?')

    const form = input.closest('form')
    expect(form).toBeTruthy()
    const submitBtn = form!.querySelector('button[type="submit"]')
    expect(submitBtn).toBeTruthy()
    await userEvent.click(submitBtn!)

    await waitFor(
      () => {
        expect(screen.getByText(/Sorry, something went wrong/)).toBeInTheDocument()
      },
      { timeout: 3000 },
    )
  })
})
