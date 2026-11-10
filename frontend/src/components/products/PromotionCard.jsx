import { BadgePercent, CalendarDays } from 'lucide-react'
export default function PromotionCard({ promotion }) {
  return <article className="promotion-card" data-testid="promotion-card">
    <BadgePercent className="promo-icon" /><div><h3>{promotion.title}</h3>
    <p>{promotion.description || 'Description unavailable'}</p>
    <p className="chat-muted"><CalendarDays size={14} /> {promotion.starts_at || 'Unknown'} — {promotion.ends_at || 'Unknown'}</p>
    <p><strong>Conditions:</strong> {promotion.conditions || 'Not provided'}</p>
    <span className="category-chip">{promotion.category || (promotion.product_id ? `Product ${promotion.product_id}` : 'All eligible products')}</span></div>
  </article>
}
