import { ExternalLink, HardDrive, Microchip, PackageCheck, PackageX } from 'lucide-react'

const specValue = (spec) => {
  const value = spec.value_num ?? spec.value_text
  return value == null ? 'N/A' : `${value}${spec.unit ? ` ${spec.unit}` : ''}`
}

export default function ProductCard({ product }) {
  const specs = Object.fromEntries((product.specs || []).map((item) => [item.key, specValue(item)]))
  const demo = product.name.startsWith('TEST-')
  return <article className="chat-product-card" data-testid="product-card">
    <div className="card-topline">
      <span className="category-chip">{product.category}</span>
      {demo && <span className="demo-chip">Demo product</span>}
    </div>
    <h3>{product.name}</h3>
    <p className="chat-muted">{product.brand || 'Brand unavailable'}</p>
    <strong className="price">{product.price == null ? 'Price unavailable' : `${product.price} ${product.currency}`}</strong>
    <div className="spec-list">
      {specs.ram_gb && <span><Microchip size={15} /> RAM {specs.ram_gb}</span>}
      {specs.storage_gb && <span><HardDrive size={15} /> Storage {specs.storage_gb}</span>}
      {specs.processor && <span><Microchip size={15} /> {specs.processor}</span>}
    </div>
    <div className={`chat-stock chat-stock-${product.in_stock}`}>
      {product.in_stock === true ? <><PackageCheck size={16} /> In stock</> :
        product.in_stock === false ? <><PackageX size={16} /> Out of stock</> : <>Availability unknown</>}
    </div>
    {product.url && <a href={product.url} target="_blank" rel="noreferrer">View product <ExternalLink size={14} /></a>}
  </article>
}
