import { Bot, User } from 'lucide-react'
import ProductGrid from '../products/ProductGrid'
import ComparisonTable from '../products/ComparisonTable'
import RecommendationCard from '../products/RecommendationCard'
import PromotionCard from '../products/PromotionCard'

const isRtl = (text) => /[\u0600-\u06ff]/.test(text)
export default function ChatMessage({ message }) {
  const response = message.response
  return <article className={`message-row ${message.role}`} dir={isRtl(message.text) ? 'rtl' : 'ltr'}>
    <div className="avatar">{message.role === 'user' ? <User size={17} /> : <Bot size={17} />}</div>
    <div className="message-content"><div className="bubble">{message.text}</div>
      {response && <div className="structured-results" dir="ltr">
        {response.intent !== 'recommendation' && <ProductGrid products={response.intent === 'comparison' ? [] : response.products} />}
        <ComparisonTable comparison={response.comparison} products={response.products} />
        {!!response.recommendations?.length && <div className="recommendation-grid">{response.recommendations.map((item) => <RecommendationCard key={item.product.id} item={item} />)}</div>}
        {!!response.promotions?.length && <div className="promotion-grid">{response.promotions.map((item) => <PromotionCard key={item.id} promotion={item} />)}</div>}
      </div>}
      <time>{message.at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div>
  </article>
}
