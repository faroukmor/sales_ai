import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ComparisonTable from './ComparisonTable'
import PromotionCard from './PromotionCard'
import RecommendationCard from './RecommendationCard'
import { product } from '../../test/fixtures'

describe('structured business results', () => {
  it('renders comparison values without reading prose', () => {
    render(<ComparisonTable products={[product]} comparison={{ product_ids: [1], rows: [
      { attribute: 'ram_gb', values: [{ product_id: 1, value: '16 GB' }] },
    ] }} />)
    expect(screen.getByTestId('comparison-table')).toHaveTextContent('16 GB')
  })

  it('renders recommendation score, reasons and limitations', () => {
    render(<RecommendationCard item={{ rank: 1, score: '0.9000', product,
      reasons: ['Within budget'], missing_specifications: ['processor'] }} />)
    expect(screen.getByTestId('recommendation-card')).toHaveTextContent('Score 0.9000')
    expect(screen.getByText(/Missing: processor/)).toBeInTheDocument()
  })

  it('renders promotion facts as supplied', () => {
    render(<PromotionCard promotion={{ id: 2, title: 'Laptop offer', description: 'Demo offer',
      conditions: 'Eligible laptops', starts_at: '2026-01-01', ends_at: '2026-01-31',
      product_id: null, category: 'laptop', source: 'test' }} />)
    expect(screen.getByTestId('promotion-card')).toHaveTextContent('Eligible laptops')
    expect(screen.getByTestId('promotion-card')).not.toHaveTextContent('% off')
  })
})
