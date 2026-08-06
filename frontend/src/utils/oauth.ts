// Supabase Auth OAuth helpers
import { createClient } from '@supabase/supabase-js'
import type { ClientConfigResponse } from '@/api/config'

export type OAuthProvider = 'google' | 'github'

// Singleton map keyed by supabase_url to reuse the same client instance
// within the same page load. This is critical for PKCE: the same client
// that generates the code_verifier must be used to exchange the code.
const _clients = new Map<string, ReturnType<typeof createClient>>()

/**
 * Return (or create) the Supabase client for this project.
 * Using a singleton ensures the PKCE code_verifier stored in localStorage
 * is accessible when exchangeCodeForSession is called on the callback page.
 */
export function getSupabaseClient(config: ClientConfigResponse) {
  if (!config.supabase_url || !config.supabase_anon_key) {
    throw new Error('Supabase is not configured')
  }
  const key = config.supabase_url
  if (!_clients.has(key)) {
    _clients.set(
      key,
      createClient(config.supabase_url, config.supabase_anon_key, {
        auth: {
          flowType: 'pkce',
          autoRefreshToken: false,
          persistSession: true,
          // IMPORTANT: set to false so the SDK does NOT auto-consume the
          // ?code= param on page load. We call exchangeCodeForSession
          // ourselves below to keep full control of the flow.
          detectSessionInUrl: false,
        },
      }),
    )
  }
  return _clients.get(key)!
}

/**
 * Trigger Supabase OAuth sign-in flow for a given provider (google | github).
 * Uses PKCE; the code_verifier is stored in localStorage by the SDK.
 */
export async function startOAuthSignIn(
  config: ClientConfigResponse,
  provider: OAuthProvider,
): Promise<void> {
  const supabase = getSupabaseClient(config)
  const redirectTo = `${window.location.origin}/oauth/callback`
  const { error } = await supabase.auth.signInWithOAuth({
    provider,
    options: { redirectTo },
  })
  if (error) throw error
}

/**
 * Exchange the OAuth authorization code (from the callback URL) for a
 * Supabase access token. The SDK reads the stored PKCE code_verifier
 * automatically from localStorage.
 */
export async function getSessionFromOAuthCode(
  config: ClientConfigResponse,
  code: string,
): Promise<string> {
  const supabase = getSupabaseClient(config)
  const { data, error } = await supabase.auth.exchangeCodeForSession(code)
  if (error || !data.session?.access_token) {
    throw error || new Error('Failed to exchange OAuth code for session')
  }
  return data.session.access_token
}

