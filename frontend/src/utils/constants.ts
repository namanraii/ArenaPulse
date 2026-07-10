export const LANGUAGES: Record<string, string> = {
  en: 'English',
  es: 'Español',
  fr: 'Français',
  de: 'Deutsch',
  pt: 'Português',
  ar: 'العربية',
  zh: '中文',
  ja: '日本語',
}

export const getDensityClass = (d: number) => {
  if (d >= 0.9) return 'critical'
  if (d >= 0.82) return 'high'
  if (d >= 0.65) return 'watch'
  return 'calm'
}
