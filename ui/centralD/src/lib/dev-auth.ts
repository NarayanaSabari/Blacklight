/**
 * Development Authentication Helper
 * 
 * This file provides a mock authentication token for development purposes.
 * In production, this should be replaced with proper login flow.
 * 
 * TODO: Remove this once proper PM Admin authentication is implemented
 */

/**
 * Set a development token in localStorage
 * Call this function in your app initialization (e.g., main.tsx)
 */
export function setDevToken() {
  // Only set in development
  if (import.meta.env.DEV) {
    // This is a mock JWT token structure
    // In real implementation, this would come from backend login
    const mockToken = 'dev-mock-token-replace-with-real-auth';
    
    localStorage.setItem('pm_admin_token', mockToken);
    console.warn(
      '🔓 Development: Mock auth token set. Implement proper authentication before production!'
    );
  }
}

/**
 * Clear development token
 */
export function clearDevToken() {
  localStorage.removeItem('pm_admin_token');
}
