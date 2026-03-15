'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import fallbackProfileOptions from '@/constants/profile_options.json'

/** Shape from backend GET /config */
export interface AppConfig {
  profile_options: {
    dietary_preference_options: Array<{ value: string; label: string }>
    allergen_options: string[]
    lifestyle_options: Array<{ value: string; label: string }>
    diet_icon: Record<string, string>
  }
  max_chat_message_length: number
}

const FALLBACK_MAX_LENGTH = 8192

const defaultConfig: AppConfig = {
  profile_options: fallbackProfileOptions as AppConfig['profile_options'],
  max_chat_message_length: FALLBACK_MAX_LENGTH,
}

interface ConfigContextValue extends AppConfig {
  configLoaded: boolean
}

const ConfigContext = createContext<ConfigContextValue>({
  ...defaultConfig,
  configLoaded: false,
})

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<ConfigContextValue>({
    ...defaultConfig,
    configLoaded: false,
  })

  useEffect(() => {
    let cancelled = false
    fetch('/api/config')
      .then((res) => (res.ok ? res.json() : null))
      .then((data: AppConfig | null) => {
        if (cancelled || !data) return
        setConfig({
          profile_options: data.profile_options ?? defaultConfig.profile_options,
          max_chat_message_length:
            typeof data.max_chat_message_length === 'number'
              ? data.max_chat_message_length
              : FALLBACK_MAX_LENGTH,
          configLoaded: true,
        })
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <ConfigContext.Provider value={config}>
      {children}
    </ConfigContext.Provider>
  )
}

export function useConfig(): ConfigContextValue {
  return useContext(ConfigContext)
}
