import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Pencil, Trash2, X, Package, LogOut, RefreshCw } from 'lucide-react'
import { storeApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const emptyForm = { name: '', category: '', brand: '', description: '', price: '', currency: 'DZD', stock_quantity: '0', url: '', is_test_data: false }

export default function AdminProductsPage() {
  const { user, logout } = useAuth()
  const [data, setData] = useState({ items: [], total: 0, pages: 0, categories: [] })
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [form, setForm] = useState(emptyForm)
  const [editing, setEditing] = useState(null)
  const [modal, setModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [forbidden, setForbidden] = useState(false)

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

  function openCreate() { setEditing(null); setForm(emptyForm); setError(''); setModal(true) }
  function openEdit(product) {
    setEditing(product.id)
    setForm({ name: product.name || '', category: product.category || '', brand: product.brand || '', description: product.description || '', price: product.price ?? '', currency: product.currency || 'DZD', stock_quantity: product.stock_quantity ?? '0', url: product.url || '', is_test_data: !!product.is_test_data })
    setError(''); setModal(true)
  }
  function change(e) { const { name, value, type, checked } = e.target; setForm(current => ({ ...current, [name]: type === 'checkbox' ? checked : value })) }

  async function save(e) {
    e.preventDefault(); setSaving(true); setError('')
    const payload = {
      ...form,
      price: form.price === '' ? null : Number(form.price),
      stock_quantity: form.stock_quantity === '' ? null : Number(form.stock_quantity),
      in_stock: Number(form.stock_quantity || 0) > 0,
      brand: form.brand || null, description: form.description || null, url: form.url || null,
    }
    try {
      if (editing) await storeApi.updateAdminProduct(editing, payload)
      else await storeApi.createAdminProduct(payload)
      setModal(false); await load()
    } catch (e) { setError(e.message) } finally { setSaving(false) }
  }

  async function remove(product) {
    if (!window.confirm(`Delete “${product.name}” (ID ${product.id})?`)) return
    setError('')
    try { await storeApi.deleteAdminProduct(product.id); await load() }
    catch (e) { setError(e.message) }
  }

  if (forbidden) return <main className="admin-denied"><Package size={42}/><h1>Admin access only</h1><p>The signed-in account is not configured as the administrator.</p><p>Set <code>ADMIN_EMAIL</code> in the backend environment to this account's email, then restart the API.</p><Link to="/">Back to store</Link></main>

  return <main className="admin-shell">
    <header className="admin-topbar"><Link to="/" className="admin-brand">GÉANT <span>ADMIN</span></Link><div><span>{user?.email}</span><button onClick={async () => { await logout(); window.location.href = '/login' }}><LogOut size={16}/> Logout</button></div></header>
    <section className="admin-content">
      <div className="admin-heading"><div><p className="admin-eyebrow">CATALOG MANAGEMENT</p><h1>Products</h1><p>Manage the products stored in your GEANT database.</p></div><button className="admin-primary" onClick={openCreate}><Plus size={18}/> Add product</button></div>
      <div className="admin-stats"><div><Package/><span>Total products</span><strong>{data.total}</strong></div><div><span>Categories</span><strong>{data.categories.length}</strong></div></div>
      <div className="admin-toolbar"><label><Search size={17}/><input placeholder="Search name, brand or category..." value={query} onChange={e => { setQuery(e.target.value); setPage(1) }}/></label><select value={category} onChange={e => { setCategory(e.target.value); setPage(1) }}><option value="">All categories</option>{data.categories.map(c => <option key={c}>{c}</option>)}</select><button className="admin-icon-button" onClick={load} title="Refresh"><RefreshCw size={17}/></button></div>
      {error && !modal && <p className="admin-error">{error}</p>}
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Product</th><th>Category</th><th>Brand</th><th>Price</th><th>Stock</th><th>Actions</th></tr></thead><tbody>
        {loading ? <tr><td colSpan="6" className="admin-empty">Loading products...</td></tr> : data.items.length === 0 ? <tr><td colSpan="6" className="admin-empty">No products found.</td></tr> : data.items.map(p => <tr key={p.id}><td><strong>{p.name}</strong><small>#{p.id}</small></td><td>{p.category}</td><td>{p.brand || '—'}</td><td>{p.price == null ? '—' : `${Number(p.price).toLocaleString()} ${p.currency}`}</td><td><span className={p.in_stock ? 'admin-stock yes' : 'admin-stock no'}>{p.in_stock ? `${p.stock_quantity ?? 'In stock'} available` : 'Out of stock'}</span></td><td><div className="admin-actions"><button onClick={() => openEdit(p)} title="Edit"><Pencil size={16}/></button><button className="danger" onClick={() => remove(p)} title="Delete"><Trash2 size={16}/></button></div></td></tr>)}
      </tbody></table></div>
      <div className="admin-pagination"><span>{data.total} products · Page {page} of {Math.max(1, data.pages)}</span><div><button disabled={page <= 1} onClick={() => setPage(v => v - 1)}>Previous</button><button disabled={page >= data.pages} onClick={() => setPage(v => v + 1)}>Next</button></div></div>
    </section>
    {modal && <div className="admin-modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setModal(false) }}><section className="admin-modal"><header><div><p className="admin-eyebrow">PRODUCT DETAILS</p><h2>{editing ? `Edit product #${editing}` : 'Add product'}</h2></div><button onClick={() => setModal(false)}><X/></button></header><form onSubmit={save}>
      <label>Product name *<input name="name" value={form.name} onChange={change} minLength="2" maxLength="255" required/></label>
      <div className="admin-form-grid"><label>Category *<input name="category" value={form.category} onChange={change} required placeholder="e.g. smartphone"/></label><label>Brand<input name="brand" value={form.brand} onChange={change}/></label></div>
      <div className="admin-form-grid"><label>Price<input name="price" type="number" min="0" step="0.01" value={form.price} onChange={change}/></label><label>Currency<input name="currency" minLength="3" maxLength="3" value={form.currency} onChange={change} required/></label></div>
      <label>Stock quantity<input name="stock_quantity" type="number" min="0" step="1" value={form.stock_quantity} onChange={change}/></label>
      <label>Description<textarea name="description" value={form.description} onChange={change} rows="3"/></label>
      <label>Product URL<input name="url" type="url" value={form.url} onChange={change} placeholder="https://..."/></label>
      <label className="admin-checkbox"><input name="is_test_data" type="checkbox" checked={form.is_test_data} onChange={change}/> Mark as demo/test data</label>
      {error && <p className="admin-error">{error}</p>}
      <footer><button type="button" className="admin-secondary" onClick={() => setModal(false)}>Cancel</button><button className="admin-primary" disabled={saving}>{saving ? 'Saving...' : editing ? 'Save changes' : 'Create product'}</button></footer>
    </form></section></div>}
  </main>
}
