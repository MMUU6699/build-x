import en from './en'
import zh from './zh'
import ar from './ar'

export default {
  en,
  zh,
  ar
}

export type Locale = 'en' | 'zh' | 'ar'

export const availableLocales: { label: string; value: Locale }[] = [
  { label: 'English', value: 'en' },
  { label: '中文', value: 'zh' },
  { label: 'العربية', value: 'ar' }
]
