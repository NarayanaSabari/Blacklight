/**
 * Environment configuration helper
 * Provides type-safe access to environment variables
 */

export const env = {
  // API Configuration
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'https://blacklight-api-667302703024.us-central1.run.app',
  apiTimeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,

  // Application
  appName: import.meta.env.VITE_APP_NAME || 'Blacklight Central Dashboard',
  appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',

  // Environment
  environment: import.meta.env.VITE_ENVIRONMENT || 'development',
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,

  // Base path for router (e.g., '/central' for sub-path deployment)
  basePath: (import.meta.env.VITE_BASE_PATH as string)?.replace(/\/$/, '') || '',

  // Feature Flags
  enableQueryDevtools:
    import.meta.env.VITE_ENABLE_QUERY_DEVTOOLS === 'true' || import.meta.env.DEV,
} as const;

export type Env = typeof env;
