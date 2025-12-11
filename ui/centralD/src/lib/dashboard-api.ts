/**
 * Dashboard API Service
 * API calls for job matching dashboard components
 */

import { apiClient } from './api-client';

// ============================================================================
// Types
// ============================================================================

export interface DashboardStats {
  pendingQueue: number;
  activeScrapers: number;
  newRoles: number;
  jobsImported: number;
  activeApiKeys: number;
}

export interface ScrapeSession {
  id: string;
  scraperKeyId: number;
  scraperKeyName: string;
  globalRoleId: number;
  roleName: string;
  status: 'in_progress' | 'completed' | 'failed';
  jobsFound: number;
  jobsImported: number;
  startedAt: string;
  completedAt: string | null;
  errorMessage: string | null;
  durationSeconds: number | null;
}

export interface GlobalRole {
  id: number;
  name: string;
  normalizedName: string;
  category: string | null;
  seniorityLevel: string | null;
  aliases: string[];
  candidateCount: number;
  jobCount: number;
  status: 'pending' | 'approved' | 'rejected';
  queuePriority: 'urgent' | 'high' | 'normal' | 'low';
  lastScrapedAt: string | null;
  createdAt: string;
  similarRoles?: {
    id: number;
    name: string;
    similarity: number;
  }[];
}

export interface ScraperApiKey {
  id: number;
  name: string;
  keyPrefix: string;
  status: 'active' | 'paused' | 'revoked';
  totalJobsScraped: number;
  totalSessionsCompleted: number;
  lastUsedAt: string | null;
  createdAt: string;
  expiresAt: string | null;
}

export interface JobImportBatch {
  batchId: string;
  platform: string;
  importStatus: string;
  totalJobs: number;
  newJobs: number;
  updatedJobs: number;
  failedJobs: number;
  startedAt: string;
  completedAt: string | null;
}

export interface QueueStats {
  byStatus: {
    pending: number;
    processing: number;
    completed: number;
  };
  byPriority: {
    urgent: number;
    high: number;
    normal: number;
    low: number;
  };
  totalPendingCandidates: number;
  queueDepth: number;
}

// ============================================================================
// Dashboard API
// ============================================================================

export const dashboardApi = {
  /**
   * Get dashboard statistics
   */
  getStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get('/api/scraper-monitoring/stats');
    const data = response.data;
    
    return {
      pendingQueue: data.pending_queue || 0,
      activeScrapers: data.active_scrapers || 0,
      newRoles: data.pending_roles_count || data.pending_queue || 0,
      jobsImported: data.jobs_imported_today || data.jobs_imported_24h || 0,
      activeApiKeys: data.active_api_keys || 0,
    };
  },

  /**
   * Get queue statistics
   */
  getQueueStats: async (): Promise<QueueStats> => {
    const response = await apiClient.get('/api/scraper-monitoring/stats');
    return response.data.queue_stats;
  },
};

// ============================================================================
// Scraper Monitoring API
// ============================================================================

export const scraperMonitoringApi = {
  /**
   * Get active scraper sessions
   */
  getActiveSessions: async (): Promise<ScrapeSession[]> => {
    const response = await apiClient.get('/api/scraper-monitoring/sessions', {
      params: { status: 'in_progress' }
    });
    return response.data.sessions.map(mapSession);
  },

  /**
   * Get recent sessions (completed/failed)
   */
  getRecentSessions: async (limit: number = 20): Promise<ScrapeSession[]> => {
    const response = await apiClient.get('/api/scraper-monitoring/sessions', {
      params: { limit }
    });
    return response.data.sessions.map(mapSession);
  },

  /**
   * Get session by ID
   */
  getSession: async (sessionId: string): Promise<ScrapeSession> => {
    const response = await apiClient.get(`/api/scraper-monitoring/sessions/${sessionId}`);
    return mapSession(response.data);
  },
};

// ============================================================================
// Global Roles API
// ============================================================================

export const globalRolesApi = {
  /**
   * Get all global roles with optional filters
   */
  getRoles: async (params?: {
    status?: string;
    category?: string;
    search?: string;
    page?: number;
    perPage?: number;
  }): Promise<{ roles: GlobalRole[]; total: number }> => {
    const response = await apiClient.get('/api/roles', { params });
    return {
      roles: response.data.roles.map(mapRole),
      total: response.data.total,
    };
  },

  /**
   * Get pending roles for review
   */
  getPendingRoles: async (): Promise<GlobalRole[]> => {
    const response = await apiClient.get('/api/roles', {
      params: { status: 'pending' }
    });
    return response.data.roles.map(mapRole);
  },

  /**
   * Approve a pending role
   */
  approveRole: async (roleId: number): Promise<GlobalRole> => {
    const response = await apiClient.post(`/api/roles/${roleId}/approve`);
    return mapRole(response.data.role);
  },

  /**
   * Reject a pending role
   */
  rejectRole: async (roleId: number, reason?: string): Promise<void> => {
    await apiClient.post(`/api/roles/${roleId}/reject`, { reason });
  },

  /**
   * Merge one role into another
   */
  mergeRoles: async (sourceRoleId: number, targetRoleId: number): Promise<GlobalRole> => {
    const response = await apiClient.post(`/api/roles/${sourceRoleId}/merge`, {
      target_role_id: targetRoleId
    });
    return mapRole(response.data.role);
  },

  /**
   * Update role priority
   */
  updatePriority: async (roleId: number, priority: string): Promise<GlobalRole> => {
    const response = await apiClient.patch(`/api/roles/${roleId}`, {
      queue_priority: priority
    });
    return mapRole(response.data.role);
  },

  /**
   * Create a new global role
   */
  createRole: async (data: {
    name: string;
    category?: string;
    seniorityLevel?: string;
    aliases?: string[];
  }): Promise<GlobalRole> => {
    const response = await apiClient.post('/api/roles', {
      name: data.name,
      category: data.category,
      seniority_level: data.seniorityLevel,
      aliases: data.aliases,
    });
    return mapRole(response.data.role);
  },
};

// ============================================================================
// API Keys API
// ============================================================================

export const apiKeysApi = {
  /**
   * Get all API keys
   */
  getKeys: async (): Promise<ScraperApiKey[]> => {
    const response = await apiClient.get('/api/scraper-monitoring/api-keys');
    return response.data.api_keys.map(mapApiKey);
  },

  /**
   * Create a new API key
   */
  createKey: async (data: { name: string; expiresAt?: string }): Promise<{ key: ScraperApiKey; rawKey: string }> => {
    const response = await apiClient.post('/api/scraper-monitoring/api-keys', {
      name: data.name,
      expires_at: data.expiresAt,
    });
    return {
      key: mapApiKey(response.data.api_key),
      rawKey: response.data.raw_key,
    };
  },

  /**
   * Update API key status
   */
  updateKeyStatus: async (keyId: number, status: 'active' | 'paused'): Promise<ScraperApiKey> => {
    const response = await apiClient.patch(`/api/scraper-monitoring/api-keys/${keyId}`, {
      status
    });
    return mapApiKey(response.data.api_key);
  },

  /**
   * Revoke an API key
   */
  revokeKey: async (keyId: number): Promise<void> => {
    await apiClient.delete(`/api/scraper-monitoring/api-keys/${keyId}`);
  },
};

// ============================================================================
// Job Imports API
// ============================================================================

export const jobImportsApi = {
  /**
   * Get recent import batches
   */
  getRecentBatches: async (limit: number = 10): Promise<JobImportBatch[]> => {
    const response = await apiClient.get('/api/jobs/batches', {
      params: { limit }
    });
    return response.data.batches.map(mapBatch);
  },

  /**
   * Get import statistics
   */
  getStatistics: async (): Promise<{
    totalJobs: number;
    jobsByPlatform: Record<string, number>;
    totalBatches: number;
    recentImports: JobImportBatch[];
  }> => {
    const response = await apiClient.get('/api/jobs/statistics');
    return {
      totalJobs: response.data.total_jobs,
      jobsByPlatform: response.data.jobs_by_platform,
      totalBatches: response.data.total_batches,
      recentImports: response.data.recent_imports.map(mapBatch),
    };
  },
};

// ============================================================================
// Mappers (snake_case to camelCase)
// ============================================================================

function mapSession(data: Record<string, unknown>): ScrapeSession {
  return {
    id: data.id as string,
    scraperKeyId: data.scraper_key_id as number,
    scraperKeyName: data.scraper_key_name as string,
    globalRoleId: data.global_role_id as number,
    roleName: data.role_name as string,
    status: data.status as ScrapeSession['status'],
    jobsFound: data.jobs_found as number,
    jobsImported: data.jobs_imported as number,
    startedAt: data.started_at as string,
    completedAt: data.completed_at as string | null,
    errorMessage: data.error_message as string | null,
    durationSeconds: data.duration_seconds as number | null,
  };
}

function mapRole(data: Record<string, unknown>): GlobalRole {
  return {
    id: data.id as number,
    name: data.name as string,
    normalizedName: (data.normalized_name || data.name) as string,
    category: data.category as string | null,
    seniorityLevel: data.seniority_level as string | null,
    aliases: (data.aliases as string[]) || [],
    candidateCount: data.candidate_count as number,
    jobCount: (data.job_count || 0) as number,
    // Handle both 'status' and 'queue_status' field names from backend
    status: (data.status || data.queue_status) as GlobalRole['status'],
    // Handle both 'queue_priority' and 'priority' field names from backend
    queuePriority: (data.queue_priority || data.priority || 'normal') as GlobalRole['queuePriority'],
    lastScrapedAt: data.last_scraped_at as string | null,
    createdAt: data.created_at as string,
    similarRoles: data.similar_roles as GlobalRole['similarRoles'],
  };
}

function mapApiKey(data: Record<string, unknown>): ScraperApiKey {
  return {
    id: data.id as number,
    name: data.name as string,
    keyPrefix: data.key_prefix as string,
    status: data.status as ScraperApiKey['status'],
    totalJobsScraped: data.total_jobs_scraped as number,
    totalSessionsCompleted: data.total_sessions_completed as number,
    lastUsedAt: data.last_used_at as string | null,
    createdAt: data.created_at as string,
    expiresAt: data.expires_at as string | null,
  };
}

function mapBatch(data: Record<string, unknown>): JobImportBatch {
  return {
    batchId: data.batch_id as string,
    platform: data.platform as string,
    importStatus: data.import_status as string,
    totalJobs: data.total_jobs as number,
    newJobs: data.new_jobs as number,
    updatedJobs: data.updated_jobs as number,
    failedJobs: data.failed_jobs as number,
    startedAt: data.started_at as string,
    completedAt: data.completed_at as string | null,
  };
}
