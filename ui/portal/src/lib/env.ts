/**
 * Environment Configuration for Portal
 */

const getEnvVar = (key: string, defaultValue?: string): string => {
  const value = import.meta.env[key] || defaultValue;
  if (!value) {
    throw new Error(`Missing environment variable: ${key}`);
  }
  return value;
};

export const env = {
  apiBaseUrl: getEnvVar('VITE_API_BASE_URL', 'https://blacklight-api-667302703024.us-central1.run.app'),
  apiTimeout: parseInt(getEnvVar('VITE_API_TIMEOUT', '30000'), 10),
  environment: getEnvVar('VITE_ENVIRONMENT', 'development'),
} as const;
