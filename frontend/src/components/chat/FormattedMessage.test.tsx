import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import FormattedMessage from './FormattedMessage'

describe('FormattedMessage', () => {
  it('renders user messages as plain text without formatting', () => {
    render(<FormattedMessage content="Hello **world** _test_" isUser />)
    const paragraph = screen.getByText('Hello **world** _test_')
    expect(paragraph.tagName.toLowerCase()).toBe('p')
  })

  it('renders bold and italic for assistant messages', () => {
    render(<FormattedMessage content="Hello **world** and _note_." />)

    const bold = screen.getByText('world')
    const italic = screen.getByText('note')

    expect(bold.tagName.toLowerCase()).toBe('strong')
    expect(italic.tagName.toLowerCase()).toBe('em')
  })

  it('renders bullet lists with colored dots and inline formatting', () => {
    render(
      <FormattedMessage
        content={[
          '- ❌ Unsafe item',
          '- ✅ Safe item',
          '- Regular bullet with **bold**',
        ].join('\n')}
      />,
    )

    // Three list items rendered
    const items = screen.getAllByRole('listitem')
    expect(items.length).toBe(3)

    // Ensure the bold text appears inside the last bullet
    expect(screen.getByText('bold')).toBeInTheDocument()
  })

  it('renders paragraph breaks for blank lines', () => {
    render(<FormattedMessage content={'Line one\n\nLine two'} />)

    expect(screen.getByText('Line one')).toBeInTheDocument()
    expect(screen.getByText('Line two')).toBeInTheDocument()
  })

  it('underlines annotated ingredient names in verdict colors', () => {
    render(
      <FormattedMessage
        content="Gelatin is not suitable. Sugar is fine."
        annotations={[
          { name: 'Gelatin', status: 'avoid' },
          { name: 'Sugar', status: 'safe' },
        ]}
      />,
    )

    const gelatin = screen.getByText('Gelatin')
    const sugar = screen.getByText('Sugar')
    expect(gelatin.className).toContain('decoration-avoid')
    expect(sugar.className).toContain('decoration-safe')
  })

  it('annotates only the first mention so alternatives stay uncolored', () => {
    const { container } = render(
      <FormattedMessage
        content="Egg is not suitable for a Jain diet (animal-derived). Try Flax egg instead."
        annotations={[{ name: 'Egg', status: 'avoid' }]}
      />,
    )

    const annotated = container.querySelectorAll('.decoration-avoid')
    expect(annotated).toHaveLength(1)
    expect(annotated[0].textContent).toBe('Egg')
    expect(container.textContent).toContain('Flax egg')
  })
})

