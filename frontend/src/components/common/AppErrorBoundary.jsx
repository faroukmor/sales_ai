import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    if (import.meta.env.DEV) console.error('GEANT Chat UI render failure', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return <main className="fatal-error" role="alert">
      <div className="fatal-error-card">
        <AlertTriangle size={32} />
        <p className="eyebrow">GEANT CHAT UI</p>
        <h1>The interface could not start</h1>
        <p>Reload the page to try again. If the problem continues, check the browser console or contact support.</p>
        <button onClick={() => window.location.reload()}><RefreshCw size={17} /> Reload application</button>
      </div>
    </main>
  }
}
