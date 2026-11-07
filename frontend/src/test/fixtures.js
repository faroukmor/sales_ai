export const product = {
  id: 1, name: 'TEST-LAPTOP-01', brand: 'Northstar', category: 'laptop',
  description: 'Demo', price: '95000.00', currency: 'DZD', in_stock: true, url: null,
  specs: [{ key: 'ram_gb', value_num: '16', value_text: null, unit: 'GB' }],
}
export const baseResponse = {
  session_id: '2bfe01f8-1907-4c13-a2d4-671b1197bdd9', answer: 'I found one product.',
  status: 'ok', intent: 'product_search', language: 'en', products: [product],
  comparison: null, recommendations: [], promotions: [], sources: [],
}
