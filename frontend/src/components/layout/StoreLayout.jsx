import { Bot, Menu, Search, ShoppingCart, UserRound, X } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useCart } from '../../contexts/CartContext'
import ChatDrawer from '../chat/ChatDrawer'

export default function StoreLayout() {
  const { user, logout } = useAuth(); const { cart } = useCart(); const navigate = useNavigate()
  const [mobile, setMobile] = useState(false); const [chat, setChat] = useState(false); const [q, setQ] = useState('')
  const search = (e) => { e.preventDefault(); navigate(`/catalog?q=${encodeURIComponent(q)}`) }
  return <div className="store-shell">
    <div className="utility"><span>GEANT STORE — DEMO</span><span>FR · AR · EN</span></div>
    <header className="store-header">
      <Link className="brand" to="/"><span>GÉANT</span><small>STORE — DEMO</small></Link>
      <form className="header-search" onSubmit={search}><Search size={18}/><input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher des produits" placeholder="Rechercher dans le catalogue…"/></form>
      <nav className={mobile ? 'header-actions open' : 'header-actions'}>
        <NavLink to="/catalog">Produits</NavLink><button className="link-button" onClick={() => setChat(true)}><Bot size={19}/> Assistant IA</button>
        <NavLink to={user ? '/profile' : '/login'}><UserRound size={19}/>{user ? user.full_name.split(' ')[0] : 'Connexion'}</NavLink>
        <NavLink className="cart-link" to="/cart"><ShoppingCart size={20}/>Panier <b>{cart.item_count}</b></NavLink>
        {user && <button className="link-button" onClick={() => logout().then(() => navigate('/'))}>Déconnexion</button>}
      </nav>
      <button className="mobile-toggle" aria-label="Menu" onClick={() => setMobile(!mobile)}>{mobile ? <X/> : <Menu/>}</button>
    </header>
    <div className="category-strip">{['Lavage','Climatisation','Cuisson','Froid','Chauffage','Multimédia','Petit électroménager','Informatique'].map(c => <Link key={c} to={`/catalog?category=${encodeURIComponent(c)}`}>{c}</Link>)}</div>
    <main><Outlet/></main>
    <footer><div className="brand">GÉANT <small>STORE — DEMO</small></div><p>Prototype e-commerce indépendant. Produits, prix, stocks et commandes sont des données de démonstration.</p><Link to="/chat">Assistant plein écran</Link></footer>
    <button className="chat-fab" onClick={() => setChat(true)} aria-label="Ouvrir l'assistant IA"><Bot/></button>
    {chat && <ChatDrawer onClose={() => setChat(false)}/>} 
  </div>
}
