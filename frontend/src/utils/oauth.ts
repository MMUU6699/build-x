// OAuth (Supabase Auth PKCE) helpers.
// The PKCE flow runs in the browser against the shared Supabase project so it
// works regardless of the public origin (including dynamic tunnel URLs).

import type { ClientConfigResponse } from '@/api/config'

export type OAuthProvider = 'google' | 'github'

export interface OAuthPkcePair {
  verifier: string
  challenge: string
  state: string
}

const STORAGE_KEY = 'buildx_oauth_pkce'

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

function randomString(length: number): string {
  const bytes = new Uint8Array(length)
  crypto.getRandomValues(bytes)
  return base64UrlEncode(bytes).slice(0, length)
}

/**
 * Generate a PKCE verifier / code_challenge / state triplet.
 */
export async function generatePkcePair(): Promise<OAuthPkcePair> {
  const verifier = randomString(64)
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  const challenge = base64UrlEncode(new Uint8Array(digest))
  return {
    verifier,
    challenge,
    state: randomString(32),
  }
}

/**
 * Persist the PKCE pair keyed by state so the callback page can resume it.
 */
export function storePkcePair(pair: OAuthPkcePair): void {
  sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ verifier: pair.verifier, state: pair.state, created: Date.now() })
  )
}

/**
 * Read and remove the stored PKCE pair for a given state.
 */
export function consumePkcePair(state: string): OAuthPkcePair | null {
  const raw = sessionStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  const parsed = JSON.parse(raw) as { verifier: string; state: string; created: number }
  // 10 minute expiry, matching typical OAuth authorization lifetime.
  if (parsed.state !== state || Date.now() - parsed.created > 10 * 60 * 1000) {
    sessionStorage.removeItem(STORAGE_KEY)
    return null
  }
  sessionStorage.removeItem(STORAGE_KEY)
  return { verifier: parsed.verifier, challenge: '', state: parsed.state }
}

/**
 * Build the Supabase OAuth authorize URL (PKCE flow) for a provider.
 */
export function buildOAuthAuthorizeUrl(
  config: ClientConfigResponse,
  provider: OAuthProvider,
  pair: OAuthPkcePair,
): string {
  const params = new URLSearchParams({
    provider,
    redirect_to: `${window.location.origin}/oauth/callback`,
    flow_type: 'pkce',
    code_challenge: pair.challenge,
    code_challenge_method: 'S256',
    state: pair.state,
  })
  return `${config.supabase_url?.replace(/\/+$/, '')}/auth/v1/authorize?${params.toString()}`
}

/**
 * Exchange the OAuth authorization code for a Supabase access token.
 */
export async function exchangeOAuthCode(
  config: ClientConfigResponse,
  code: string,
  verifier: string,
): Promise<{ access_token: string; refresh_token?: string }> {
  const url = `${config.supabase_url?.replace(/\/+$/, '')}/auth/v1/token?grant_type=pkce`
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: config.supabase_anon_key || '',
    },
    body: JSON.stringify({
      auth_code: code,
      code_verifier: verifier,
    }),
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    const msg = data.error_description || data.msg || data.error || 'OAuth exchange failed'
    throw new Error(msg)
  }
  const data = await resp.json()
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
  }
}
