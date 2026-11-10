import ProductCard from './ProductCard'
export default function ProductGrid({ products = [] }) {
  return products.length ? <div className="chat-product-grid">{products.map((p) => <ProductCard key={p.id} product={p} />)}</div> : null
}
