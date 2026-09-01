import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import de from './locales/de.json'
import en from './locales/en.json'
import fr from './locales/fr.json'
import ru from './locales/ru.json'
import tr from './locales/tr.json'

// Ana dil Ingilizce - yaninda Almanca/Turkce/Rusca/Fransizca. Tercih
// localStorage'da saklanir (dil secici, bkz. layouts/*), yoksa tarayici
// dili denenir, o da yoksa Ingilizce'ye duser.
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      de: { translation: de },
      tr: { translation: tr },
      ru: { translation: ru },
      fr: { translation: fr },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'de', 'tr', 'ru', 'fr'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'lang',
    },
  })

export default i18n
