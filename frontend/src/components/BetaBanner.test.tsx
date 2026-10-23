import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import BetaBanner from './BetaBanner'
import { BETA_BANNER } from '@/constants/disclaimers'

describe('BetaBanner', () => {
  it('renders the beta disclaimer for every page', () => {
    render(<BetaBanner />)
    const banner = screen.getByTestId('beta-banner')
    expect(banner).toHaveAttribute('role', 'status')
    expect(banner).toHaveTextContent(BETA_BANNER)
  })
})
