import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import AppErrorBoundary from './components/common/AppErrorBoundary'
import './styles/globals.css'
import './styles/chat.css'
import './styles/store.css'
import './styles/admin.css'
const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('GEANT Chat UI root element is missing')
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <AppErrorBoundary><App /></AppErrorBoundary>
  </React.StrictMode>,
)
