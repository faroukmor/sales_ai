import { createContext, useContext, useEffect, useState } from 'react'
import { storeApi } from '../services/api'
import { useAuth } from './AuthContext'
const CartContext = createContext(null)
const empty = { items: [], item_count: 0, total: 0, currency: 'DZD' }
export function CartProvider({ children }) {
  const { user } = useAuth(); const [cart, setCart] = useState(empty)
  useEffect(() => { if (user) storeApi.cart().then(setCart).catch(() => setCart(empty)); else setCart(empty) }, [user])
  const run = async (operation) => { if (!user) throw new Error('Connectez-vous pour ajouter au panier'); const result = await operation(); setCart(result); return result }
  return <CartContext.Provider value={{ cart, add: (id, q) => run(() => storeApi.addCart(id, q)), update: (id, q) => run(() => storeApi.updateCart(id, q)), remove: (id) => run(() => storeApi.removeCart(id)), refresh: () => storeApi.cart().then(setCart) }}>{children}</CartContext.Provider>
}
export const useCart = () => useContext(CartContext)
