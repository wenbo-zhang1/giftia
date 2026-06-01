import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: '#F9F6F2',
          fontFamily: "'Segoe UI', 'SF Pro Display', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif",
        }}>
          <div style={{
            textAlign: 'center',
            padding: '48px',
            maxWidth: '420px',
            background: '#FFFFFF',
            borderRadius: '24px',
            boxShadow: '0 8px 24px rgba(45,36,32,0.08)',
          }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #E8A87C, #D4785C)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
              fontWeight: 700,
              margin: '0 auto 16px',
            }}>
              !
            </div>
            <h2 style={{ color: '#2D2420', marginBottom: '8px', fontSize: '20px', fontWeight: 700 }}>
              出了点问题
            </h2>
            <p style={{ color: '#7A6E64', fontSize: '14px', marginBottom: '24px', lineHeight: 1.7 }}>
              应用遇到了一个意外错误。请尝试刷新页面，如果问题持续存在，请联系开发者。
            </p>
            <details style={{ marginBottom: '20px', textAlign: 'left' }}>
              <summary style={{ cursor: 'pointer', color: '#B0A59A', fontSize: '12px' }}>
                错误详情
              </summary>
              <pre style={{
                marginTop: '8px',
                padding: '12px',
                background: '#F8F3ED',
                borderRadius: '8px',
                fontSize: '11px',
                overflow: 'auto',
                color: '#5A4E44',
                whiteSpace: 'pre-wrap',
                fontFamily: "'SF Mono', 'Fira Code', monospace",
              }}>
                {this.state.error?.message}
                {this.state.error?.stack}
              </pre>
            </details>
            <button
              onClick={this.handleReload}
              style={{
                padding: '12px 28px',
                borderRadius: '14px',
                border: 'none',
                background: '#D4785C',
                color: '#fff',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(212,120,92,0.2)',
                transition: 'background 0.2s, transform 0.15s',
              }}
              onMouseEnter={(e) => { (e.target as HTMLElement).style.background = '#C0684C' }}
              onMouseLeave={(e) => { (e.target as HTMLElement).style.background = '#D4785C' }}
            >
              重试
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}