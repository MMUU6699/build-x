<template>
  <div class="w-full min-h-[100vh] relative bg-[var(--background-gray-main)] dark:bg-[#050505]">
    <div class="relative z-[1] flex flex-col justify-center items-center min-h-[100vh] pt-[20px] pb-[60px]">
      <div class="flex flex-col items-center gap-[20px]">
        <div class="w-[80px] h-[80px] text-[var(--icon-primary)]">
          <LoaderCircle :size="80" class="animate-spin" />
        </div>
        <h1 class="text-[20px] font-bold text-center text-[var(--text-primary)] max-sm:text-[18px]">
          {{ t('Signing in...') }}
        </h1>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { LoaderCircle } from 'lucide-vue-next'
import {
  getCachedClientConfig,
  getCachedAuthProvider,
} from '@/api/config'
import {
  oauthLogin,
  storeToken,
  storeRefreshToken,
  setAuthToken,
} from '@/api/auth'
import { consumePkcePair, exchangeOAuthCode } from '@/utils/oauth'
import { showErrorToast, showSuccessToast } from '@/utils/toast'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

onMounted(async () => {
  try {
    const authProvider = await getCachedAuthProvider()
    if (!authProvider || authProvider === 'none') {
      router.replace('/login')
      return
    }

    const params = route.query
    if (params.error) {
      const description = (params.error_description || params.error) as string
      showErrorToast(description)
      router.replace('/login')
      return
    }

    const code = params.code as string | undefined
    const state = params.state as string | undefined
    if (!code || !state) {
      showErrorToast(t('OAuth login failed, please try again'))
      router.replace('/login')
      return
    }

    const pair = consumePkcePair(state)
    if (!pair) {
      showErrorToast(t('OAuth login expired, please try again'))
      router.replace('/login')
      return
    }

    const config = await getCachedClientConfig()
    if (!config?.supabase_url || !config?.supabase_anon_key) {
      showErrorToast(t('OAuth is not configured'))
      router.replace('/login')
      return
    }

    const { access_token } = await exchangeOAuthCode(config, code, pair.verifier)
    const response = await oauthLogin({ access_token })

    storeToken(response.access_token)
    storeRefreshToken(response.refresh_token)
    setAuthToken(response.access_token)

    showSuccessToast(t('Login successful! Welcome back'))
    const redirect = route.query.redirect as string | undefined
    router.replace(redirect && redirect.startsWith('/') ? redirect : '/')
  } catch (error) {
    console.error('OAuth callback failed:', error)
    showErrorToast(t('OAuth login failed, please try again'))
    router.replace('/login')
  }
})
</script>
