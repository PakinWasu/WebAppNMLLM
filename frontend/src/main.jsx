import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
  state = { error: null }
  static getDerivedStateFromError(error) {
    return { error }
  }
  componentDidCatch(error, info) {
    console.error('React Error Boundary:', error, info)
  }
  retry = () => {
    this.setState({ error: null })
  }
  render() {
    if (this.state.error) {
      const msg = this.state.error?.message || String(this.state.error)
      return (
        <div style={{ padding: 24, fontFamily: 'sans-serif', background: '#0f172a', color: '#e2e8f0', minHeight: '100vh' }}>
          <h2 style={{ color: '#f87171' }}>Something went wrong</h2>
          <pre style={{ background: '#1e293b', padding: 16, borderRadius: 8, overflow: 'auto' }}>{msg}</pre>
          <p style={{ marginTop: 16 }}>If you see &quot;Objects are not valid as a React child&quot;, the app tried to display an object. You can try again or refresh the page.</p>
          <button
            type="button"
            onClick={this.retry}
            style={{ marginTop: 16, padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            Try again
          </button>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{ marginTop: 16, marginLeft: 8, padding: '8px 16px', background: '#475569', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            Refresh page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
 <React.StrictMode>
  <ErrorBoundary>
   <App />
  </ErrorBoundary>
 </React.StrictMode>,
)
