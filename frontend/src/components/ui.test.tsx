import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui'

describe('UI states', () => {
  it('renders empty state', () => {
    render(<EmptyState title="No persons found" detail="Pipeline output populates IdentityStore." />)
    expect(screen.getByText('No persons found')).toBeTruthy()
    expect(screen.getByText(/Pipeline output/)).toBeTruthy()
  })

  it('renders error state', () => {
    render(<ErrorState message="Not authenticated" />)
    expect(screen.getByText('Not authenticated')).toBeTruthy()
  })

  it('renders loading state', () => {
    render(<LoadingState label="Loading persons…" />)
    expect(screen.getByText('Loading persons…')).toBeTruthy()
  })
})
