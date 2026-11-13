import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink, Info, LogOut, Package, Pencil, Plus, RefreshCw, Search, Store, Trash2, X } from 'lucide-react'
import { storeApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const OTHER = '__other'
const emptyForm = { name: '', typeKey: '', customCategory: '', brand: '', description: '', price: '', currency: 'DZD', stock_quantity: '0', url: '', is_test_data: false }

let rowId = 0
const newRow = (row = {}) => ({ id: ++rowId, label: '', value: '', unit: '', origKey: '', ...row })
const humanize = (key) => { const text = key.replace(/_/g, ' ').trim(); return text.charAt(0).toUpperCase() + text.slice(1) }
const slug = (label) => label.trim().toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
const isNumeric = (text) => /^-?\d+([.,]\d+)?$/.test(text.trim())

export default function AdminProductsPage() {
  const { user, logout } = useAuth()
  const [data, setData] = useState({ items: [], total: 0, pages: 0, categories: [] })
  const [schema, setSchema] = useState({ groups: [] })
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [form, setForm] = useState(emptyForm)
  const [specValues, setSpecValues] = useState({})
  const [customSpecs, setCustomSpecs] = useState([])
  const [editing, setEditing] = useState(null)
  const [modal, setModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState(null)
  const [forbidden, setForbidden] = useState(false)

  const typeMap = useMemo(() => Object.fromEntries(schema.groups.flatMap(group => group.types.map(type => [type.key, type]))), [schema])
  const template = typeMap[form.typeKey]?.fields ?? []
  const labelOf = key => typeMap[key?.toLowerCase()]?.label ?? key

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const result = await storeApi.adminProducts({ q: query, category, page, page_size: 25 })
      setData(result); setForbidden(false)
    } catch (e) {
      if (e.message.toLowerCase().includes('administrator')) setForbidden(true)
      else setError(e.message)
    } finally { setLoading(false) }
  }, [query, category, page])

  useEffect(() => { load() }, [load])
  useEffect(() => { storeApi.adminSchema().then(setSchema).catch(() => {}) }, [])

  function openCreate() {
    setEditing(null); setForm(emptyForm); setSpecValues({}); setCustomSpecs([]); setError(''); setModal(true)
  }

  function openEdit(product) {
    const known = typeMap[product.category?.toLowerCase()]
    const typeKey = known ? known.key : OTHER
    const keys = new Set((known?.fields ?? []).map(field => field.key))
    const values = {}; const custom = []
    for (const spec of product.specs ?? []) {
      const text = String(spec.value_num ?? spec.value_text ?? '')
      if (keys.has(spec.key)) values[spec.key] = text
      else custom.push(newRow({ label: humanize(spec.key), origKey: spec.key, value: text, unit: spec.unit || '' }))
    }
    setEditing(product.id)
    setForm({ name: product.name || '', typeKey, customCategory: known ? '' : product.category || '', brand: product.brand || '', description: product.description || '', price: product.price ?? '', currency: product.currency || 'DZD', stock_quantity: product.stock_quantity ?? '0', url: product.url || '', is_test_data: !!product.is_test_data })
    setSpecValues(values); setCustomSpecs(custom); setError(''); setModal(true)
  }

  function change(e) { const { name, value, type, checked } = e.target; setForm(current => ({ ...current, [name]: type === 'checkbox' ? checked : value })) }

  function changeType(newKey) {
    const oldTemplate = typeMap[form.typeKey]?.fields ?? []
    const newKeys = new Set((typeMap[newKey]?.fields ?? []).map(field => field.key))
    const kept = {}; const moved = []
    for (const [key, value] of Object.entries(specValues)) {
      if (!String(value).trim()) continue
      if (newKeys.has(key)) kept[key] = value
      else if (editing) { const field = oldTemplate.find(item => item.key === key); moved.push(newRow({ label: field?.label ?? humanize(key), origKey: key, value, unit: field?.unit ?? '' })) }
    }
    const custom = []
    for (const row of [...customSpecs, ...moved]) {
      const key = row.origKey || slug(row.label)
      if (newKeys.has(key) && !(key in kept)) kept[key] = row.value
      else custom.push(row)
    }
    setForm(current => ({ ...current, typeKey: newKey })); setSpecValues(kept); setCustomSpecs(custom)
  }

  const setSpec = (key, value) => setSpecValues(current => ({ ...current, [key]: value }))
  const setRow = (id, patch) => setCustomSpecs(rows => rows.map(row => row.id === id ? { ...row, ...patch } : row))

  function buildSpecs() {
    const specs = []; const seen = new Set()
    for (const field of template) {
      const raw = String(specValues[field.key] ?? '').trim()
      if (!raw) continue
      if (field.kind === 'number') {
        const number = Number(raw.replace(',', '.'))
        if (!Number.isFinite(number) || number < 0) throw new Error(`${field.label}: enter a valid number`)
        specs.push({ key: field.key, value_num: number, unit: field.unit })
      } else specs.push({ key: field.key, value_text: raw })
      seen.add(field.key)
    }
    for (const row of customSpecs) {
      const label = row.label.trim(); const value = row.value.trim()
      if (!label && !value) continue
      if (!label || !value) throw new Error('Each additional specification needs both a name and a value')
      let key = row.origKey && label === humanize(row.origKey) ? row.origKey : slug(label)
      if (!key) throw new Error(`Use Latin letters or numbers in the specification name “${label}”`)
      if (!/^[a-z]/.test(key)) key = `spec_${key}`
      if (seen.has(key)) throw new Error(`The specification “${label}” is listed twice`)
      seen.add(key)
      const spec = isNumeric(value) ? { key, value_num: Number(value.replace(',', '.')) } : { key, value_text: value }
      if (row.unit.trim()) spec.unit = row.unit.trim()
      specs.push(spec)
    }
    return specs
  }

  async function save(e) {
    e.preventDefault(); setError('')
    if (!form.typeKey) { setError('Choose a product type first.'); return }
    const categoryValue = form.typeKey === OTHER ? form.customCategory.trim() : form.typeKey
    if (categoryValue.length < 2) { setError('Enter the category name.'); return }
    let specs
    try { specs = buildSpecs() } catch (err) { setError(err.message); return }
    setSaving(true)
    const { typeKey, customCategory, ...base } = form
    const payload = {
      ...base, category: categoryValue, specs,
      price: form.price === '' ? null : Number(form.price),
      stock_quantity: form.stock_quantity === '' ? null : Number(form.stock_quantity),
      in_stock: Number(form.stock_quantity || 0) > 0,
      brand: form.brand || null, description: form.description || null, url: form.url || null,
    }
    try {
      const saved = editing ? await storeApi.updateAdminProduct(editing, payload) : await storeApi.createAdminProduct(payload)
      setModal(false); setNotice({ id: saved.id, name: saved.name, created: !editing }); await load()
    } catch (err) { setError(err.message) } finally { setSaving(false) }
  }

  async function remove(product) {
    if (!window.confirm(`Delete “${product.name}” (ID ${product.id})?`)) return
    setError(''); setNotice(null)
    try { await storeApi.deleteAdminProduct(product.id); await load() }
    catch (e) { setError(e.message) }
  }

  if (forbidden) return <main className="admin-denied"><Package size={42}/><h1>Admin access only</h1><p>The signed-in account is not configured as the administrator.</p><p>Set <code>ADMIN_EMAIL</code> in the backend environment to this account's email, then restart the API.</p><Link to="/">Back to store</Link></main>

  const selectedType = typeMap[form.typeKey]
  const assistantUnsupported = form.typeKey === OTHER || selectedType?.assistant_supported === false

  return <main className="admin-shell">
    <header className="admin-topbar">
      <Link to="/" className="admin-brand">GÉANT <span>ADMIN</span></Link>
      <div>
        <Link to="/" className="admin-site-link"><Store size={16}/> View store</Link>
        <span>{user?.email}</span>
        <button onClick={async () => { await logout(); window.location.href = '/login' }}><LogOut size={16}/> Logout</button>
      </div>
    </header>
    <section className="admin-content">
      <div className="admin-heading"><div><p className="admin-eyebrow">CATALOG MANAGEMENT</p><h1>Products</h1><p>Manage the products stored in your GEANT database.</p></div><button className="admin-primary" onClick={openCreate}><Plus size={18}/> Add product</button></div>
      {notice && <p className="admin-notice">Product “{notice.name}” {notice.created ? 'created' : 'updated'}. <Link to={`/products/${notice.id}`}>View it in the store <ExternalLink size={14}/></Link><button onClick={() => setNotice(null)} aria-label="Dismiss"><X size={15}/></button></p>}
      <div className="admin-stats"><div><Package/><span>Total products</span><strong>{data.total}</strong></div><div><span>Categories</span><strong>{data.categories.length}</strong></div></div>
      <div className="admin-toolbar"><label><Search size={17}/><input placeholder="Search name, brand or category..." value={query} onChange={e => { setQuery(e.target.value); setPage(1) }}/></label><select value={category} onChange={e => { setCategory(e.target.value); setPage(1) }}><option value="">All categories</option>{data.categories.map(c => <option key={c} value={c}>{labelOf(c)}</option>)}</select><button className="admin-icon-button" onClick={load} title="Refresh"><RefreshCw size={17}/></button></div>
      {error && !modal && <p className="admin-error">{error}</p>}
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Product</th><th>Category</th><th>Brand</th><th>Price</th><th>Stock</th><th>Actions</th></tr></thead><tbody>
        {loading ? <tr><td colSpan="6" className="admin-empty">Loading products...</td></tr> : data.items.length === 0 ? <tr><td colSpan="6" className="admin-empty">No products found.</td></tr> : data.items.map(p => <tr key={p.id}><td><strong>{p.name}</strong><small>#{p.id} · {p.specs?.length ?? 0} specs</small></td><td>{labelOf(p.category)}</td><td>{p.brand || '—'}</td><td>{p.price == null ? '—' : `${Number(p.price).toLocaleString()} ${p.currency}`}</td><td><span className={p.in_stock ? 'admin-stock yes' : 'admin-stock no'}>{p.in_stock ? `${p.stock_quantity ?? 'In stock'} available` : 'Out of stock'}</span></td><td><div className="admin-actions"><Link to={`/products/${p.id}`} target="_blank" rel="noreferrer" title="View in store"><ExternalLink size={16}/></Link><button onClick={() => openEdit(p)} title="Edit"><Pencil size={16}/></button><button className="danger" onClick={() => remove(p)} title="Delete"><Trash2 size={16}/></button></div></td></tr>)}
      </tbody></table></div>
      <div className="admin-pagination"><span>{data.total} products · Page {page} of {Math.max(1, data.pages)}</span><div><button disabled={page <= 1} onClick={() => setPage(v => v - 1)}>Previous</button><button disabled={page >= data.pages} onClick={() => setPage(v => v + 1)}>Next</button></div></div>
    </section>
    {modal && <div className="admin-modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setModal(false) }}><section className="admin-modal"><header><div><p className="admin-eyebrow">PRODUCT DETAILS</p><h2>{editing ? `Edit product #${editing}` : 'Add product'}</h2></div><button onClick={() => setModal(false)} aria-label="Close"><X/></button></header><form onSubmit={save}>
      <label>Product name *<input name="name" value={form.name} onChange={change} minLength="2" maxLength="255" required/></label>
      <div className="admin-form-grid">
        <label>Product type *<select value={form.typeKey} onChange={e => changeType(e.target.value)} required>
          <option value="" disabled>Choose a type…</option>
          {schema.groups.map(group => <optgroup key={group.name} label={group.name}>{group.types.map(type => <option key={type.key} value={type.key}>{type.label}</option>)}</optgroup>)}
          <option value={OTHER}>Other (custom category)</option>
        </select></label>
        <label>Brand<input name="brand" value={form.brand} onChange={change}/></label>
      </div>
      {form.typeKey === OTHER && <label>Category name *<input name="customCategory" value={form.customCategory} onChange={change} minLength="2" maxLength="100" required placeholder="e.g. Accessories"/></label>}
      {assistantUnsupported && form.typeKey && <p className="admin-note"><Info size={16}/> This product will appear in the store. The AI assistant currently only searches laptops, smartphones and TVs, so it will not recommend this type yet.</p>}
      <div className="admin-form-grid"><label>Price<input name="price" type="number" min="0" step="0.01" value={form.price} onChange={change}/></label><label>Currency<input name="currency" minLength="3" maxLength="3" value={form.currency} onChange={change} required/></label></div>
      <label>Stock quantity<input name="stock_quantity" type="number" min="0" step="1" value={form.stock_quantity} onChange={change}/></label>

      <h3 className="admin-section-title">Specifications{selectedType ? ` — ${selectedType.label}` : ''}</h3>
      {!form.typeKey && <p className="admin-hint">Choose a product type to see its specification fields (RAM, storage, screen size, capacity…).</p>}
      {template.length > 0 && <div className="admin-form-grid">{template.map(field => {
        const value = specValues[field.key] ?? ''
        const options = field.kind === 'select' && value && !field.options.includes(value) ? [value, ...field.options] : field.options
        return <label key={field.key}><span>{field.label}{field.unit && <em> ({field.unit})</em>}</span>
          {field.kind === 'select'
            ? <select value={value} onChange={e => setSpec(field.key, e.target.value)}><option value="">—</option>{options.map(option => <option key={option} value={option}>{option}</option>)}</select>
            : <><input type={field.kind === 'number' ? 'number' : 'text'} min={field.kind === 'number' ? 0 : undefined} step={field.kind === 'number' ? 'any' : undefined} list={field.options.length ? `options-${field.key}` : undefined} value={value} onChange={e => setSpec(field.key, e.target.value)} placeholder={field.options.length ? `e.g. ${field.options[0]}` : ''}/>{field.options.length > 0 && <datalist id={`options-${field.key}`}>{field.options.map(option => <option key={option} value={option}/>)}</datalist>}</>}
        </label>
      })}</div>}
      {form.typeKey && <div className="admin-custom-specs">
        <p className="admin-hint">Anything else? Add your own specifications.</p>
        {customSpecs.map(row => <div className="admin-custom-row" key={row.id}>
          <input aria-label="Specification name" placeholder="Name (e.g. Bluetooth version)" value={row.label} onChange={e => setRow(row.id, { label: e.target.value })}/>
          <input aria-label="Specification value" placeholder="Value" value={row.value} onChange={e => setRow(row.id, { value: e.target.value })}/>
          <input aria-label="Specification unit" placeholder="Unit" value={row.unit} onChange={e => setRow(row.id, { unit: e.target.value })}/>
          <button type="button" className="admin-icon-button" title="Remove" onClick={() => setCustomSpecs(rows => rows.filter(item => item.id !== row.id))}><X size={16}/></button>
        </div>)}
        <button type="button" className="admin-secondary" onClick={() => setCustomSpecs(rows => [...rows, newRow()])}><Plus size={15}/> Add specification</button>
      </div>}

      <label>Description<textarea name="description" value={form.description} onChange={change} rows="3"/></label>
      <label>Product URL<input name="url" type="url" pattern="https?://.+" title="Must start with http:// or https://" value={form.url} onChange={change} placeholder="https://..."/></label>
      <label className="admin-checkbox"><input name="is_test_data" type="checkbox" checked={form.is_test_data} onChange={change}/> Mark as demo/test data</label>
      {error && <p className="admin-error">{error}</p>}
      <footer><button type="button" className="admin-secondary" onClick={() => setModal(false)}>Cancel</button><button className="admin-primary" disabled={saving}>{saving ? 'Saving...' : editing ? 'Save changes' : 'Create product'}</button></footer>
    </form></section></div>}
  </main>
}
