<template>
  <div class="flex flex-col gap-[12px]">
    <div class="flex items-center gap-[12px]">
      <span class="h-px flex-1 bg-[var(--border-gray)]" />
      <span class="text-[13px] text-[var(--text-tertiary)]">{{ t('Or continue with') }}</span>
      <span class="h-px flex-1 bg-[var(--border-gray)]" />
    </div>

    <button type="button"
      class="inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors h-[40px] px-[16px] rounded-[10px] gap-[8px] text-sm w-full border border-[var(--border-gray)] hover:opacity-80 active:opacity-70 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="busy !== null" @click="handleClick('google')">
      <LoaderCircle v-if="busy === 'google'" :size="16" class="animate-spin" />
      <GoogleIcon v-else :size="16" />
      <span>{{ t('Continue with Google') }}</span>
    </button>

    <button type="button"
      class="inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors h-[40px] px-[16px] rounded-[10px] gap-[8px] text-sm w-full border border-[var(--border-gray)] hover:opacity-80 active:opacity-70 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="busy !== null" @click="handleClick('github')">
      <LoaderCircle v-if="busy === 'github'" :size="16" class="animate-spin" />
      <GithubIcon v-else :size="16" />
      <span>{{ t('Continue with GitHub') }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { LoaderCircle } from 'lucide-vue-next'
import GoogleIcon from '@/components/icons/GoogleIcon.vue'
import GithubIcon from '@/components/icons/GithubIcon.vue'
import { getCachedClientConfig } from '@/api/config'
import { showErrorToast } from '@/utils/toast'
import { startOAuthSignIn, type OAuthProvider } from '@/utils/oauth'

const { t } = useI18n()

const busy = ref<OAuthProvider | null>(null)

const handleClick = async (provider: OAuthProvider) => {
  if (busy.value) return
  busy.value = provider
  try {
    const config = await getCachedClientConfig()
    if (!config?.supabase_url || !config?.supabase_anon_key) {
      showErrorToast(t('OAuth is not configured'))
      return
    }
    await startOAuthSignIn(config, provider)
  } catch (error) {
    console.error(`OAuth start failed (${provider}):`, error)
    showErrorToast(t('OAuth login failed, please try again'))
  } finally {
    busy.value = null
  }
}

</script>
