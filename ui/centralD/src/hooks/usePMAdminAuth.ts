/**
 * Custom hook for PM Admin authentication
 * Exported separately to support Fast Refresh
 */

import { useContext } from 'react';
import { PMAdminAuthContext } from '@/contexts/PMAdminAuthContext';

export function usePMAdminAuth() {
  const context = useContext(PMAdminAuthContext);
  if (context === undefined) {
    throw new Error('usePMAdminAuth must be used within PMAdminAuthProvider');
  }
  return context;
}
