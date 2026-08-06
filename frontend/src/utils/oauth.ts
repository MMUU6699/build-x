// Official Supabase Auth OAuth helpers using @supabase/supabase-js SDK
import { createClient } from '@supabase/supabase-js'
import type { ClientConfigResponse } from '@/api/config'

export type OAuthProvider = 'google' | 'github'

/**
 * Initialize a Supabase client with PKCE auth flow.
 */
export function getSupabaseClient(config: ClientConfigResponse) {
  if (!config.supabase_url || !config.supabase_anon_key) {
    throw new Error('Supabase is not configured')
  }
  return createClient(config.supabase_url, config.supabase_anon_key, {
    auth: {
      flowType: 'pkce',
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  })
}

/**
 * Trigger Supabase OAuth sign-in flow for a given provider (google | github).
 */
export async function startOAuthSignIn(
  config: ClientConfigResponse,
  provider: OAuthProvider,
): Promise<void> {
  const supabase = getSupabaseClient(config)
  const redirectTo = `${window.location.origin}/oauth/callback`
  const { error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo,
    },
  })
  if (error) {
    throw error
  }
}

/**
 * Exchange OAuth authorization code for a Supabase session.
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

