import { Award, AlertCircle } from 'lucide-react'
import ProductCard from './ProductCard'
export default function RecommendationCard({ item }) {
  return <article className="recommendation-card" data-testid="recommendation-card">
    <div className="rank"><Award size={18} /> Rank #{item.rank} <span>Score {item.score}</span></div>
    <ProductCard product={item.product} />
    <ul>{item.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
    {!!item.missing_specifications.length && <p className="limitation"><AlertCircle size={15} /> Missing: {item.missing_specifications.join(', ')}</p>}
  </article>
}
