import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { render } from '@testing-library/react'
import App from '../App'

const originalFetch = globalThis.fetch

function mockResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeAll(() => {
  Element.prototype.scrollIntoView = () => {}
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
    if (url.includes('/health')) {
      return mockResponse({ status: 'ok', auth_required: false, admin_key_configured: false })
    }
    if (url.includes('/users')) {
      return mockResponse([])
    }
    if (url.includes('/conversations')) {
      return mockResponse({ conversations: [], current_id: '' })
    }
    if (url.includes('/memory')) {
      return mockResponse({ total: 0, avg_importance: 0, consolidated_count: 0 })
    }
    if (url.includes('/config/model')) {
      return mockResponse({ model: 'test', base_url: '', multimodal: false })
    }
    return mockResponse({})
  }) as typeof fetch
})

afterAll(() => {
  globalThis.fetch = originalFetch
})

describe('App', () => {
  it('should render without crashing', () => {
    const { container } = render(<App />)
    expect(container).toBeTruthy()
  })
})