export default function ComparisonTable({ comparison, products = [] }) {
  if (!comparison) return null
  const names = Object.fromEntries(products.map((product) => [product.id, product.name]))
  return <div className="comparison-wrap" data-testid="comparison-table">
    <table><thead><tr><th>Attribute</th>{comparison.product_ids.map((id) => <th key={id}>{names[id] || `Product ${id}`}</th>)}</tr></thead>
      <tbody>{comparison.rows.map((row) => <tr key={row.attribute}><th>{row.attribute.replaceAll('_', ' ')}</th>
        {comparison.product_ids.map((id) => <td key={id}>{row.values.find((v) => v.product_id === id)?.value ?? 'N/A'}</td>)}</tr>)}</tbody>
    </table>
  </div>
}
