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
  id: number;
  sessionId: string;  // UUID - use this for API calls
  scraperKeyId: number;
  scraperKeyName: string;
  globalRoleId: number;
  roleName: string;
  status: 'in_progress' | 'completed' | 'failed' | 'terminated';
  jobsFound: number;
  jobsImported: number;
  jobsSkipped: number;
  platformsTotal: number;
  platformsCompleted: number;
  platformsFailed: number;
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
  source: 'scraper' | 'manual_import';
  platform?: string;
  importStatus: string;
  roleName?: string;
  scraperName?: string;
  
  // Job counts
  totalJobs: number;
  newJobs: number;
  updatedJobs: number;
  skippedJobs: number;
  failedJobs: number;
  
  // Platform summary
  platformsTotal: number;
  platformsCompleted: number;
  platformsFailed: number;
  platformsPending: number;
  
  // Timing
  startedAt: string;
  completedAt: string | null;
  durationSeconds: number | null;
  durationFormatted: string | null;
  
  // Error info
  errorMessage: string | null;
  sessionNotes: string | null;
  
  // Platform breakdown
  platforms: PlatformStatus[];
}

export interface PlatformStatus {
  platformName: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  statusLabel: string;
  jobsFound: number;
  jobsImported: number;
  jobsSkipped: number;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  durationSeconds: number | null;
  durationFormatted: string | null;
}

export interface ImportStatsSummary {
  totalSessions: number;
  successfulSessions: number;
  failedSessions: number;
  inProgressSessions: number;
  timeoutSessions: number;
  successRate: number;
  totalJobsImported: number;
  totalJobsSkipped: number;
  totalJobsFound: number;
  avgJobsPerSession: number;
  avgDurationSeconds: number;
}

export interface PlatformHealth {
  totalAttempts: number;
  successful: number;
  failed: number;
  successRate: number;
  jobsImported: number;
  jobsSkipped: number;
  avgDurationSeconds: number;
}

export interface ImportStatistics {
  totalJobs: number;
  jobsByPlatform: Record<string, number>;
  totalBatches: number;
  recentImports: JobImportBatch[];
  summary: ImportStatsSummary;
  platformHealth: Record<string, PlatformHealth>;
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

export interface ScraperStats {
  activeScrapers: number;
  pendingQueue: number;
  jobsStats24h: {
    totalFound: number;
    totalImported: number;
    totalSkipped: number;
    successRate: number;
  };
  sessions24h: {
    total: number;
    completed: number;
    failed: number;
    inProgress: number;
    timeout: number;
  };
  avgDurationSeconds: number;
  totalApiKeys: number;
  activeApiKeys: number;
}

export const scraperMonitoringApi = {
  /**
   * Get scraper statistics
   */
  getStats: async (): Promise<ScraperStats> => {
    const response = await apiClient.get('/api/scraper-monitoring/stats');
    const data = response.data;
    return {
      activeScrapers: data.active_scrapers || 0,
      pendingQueue: data.pending_queue || 0,
      jobsStats24h: {
        totalFound: data.jobs_stats_24h?.total_found || 0,
        totalImported: data.jobs_stats_24h?.total_imported || 0,
        totalSkipped: data.jobs_stats_24h?.total_skipped || 0,
        successRate: data.jobs_stats_24h?.success_rate || 0,
      },
      sessions24h: {
        total: data.sessions_24h?.total || 0,
        completed: data.sessions_24h?.completed || 0,
        failed: data.sessions_24h?.failed || 0,
        inProgress: data.sessions_24h?.in_progress || 0,
        timeout: data.sessions_24h?.timeout || 0,
      },
      avgDurationSeconds: data.avg_duration_seconds || 0,
      totalApiKeys: data.total_api_keys || 0,
      activeApiKeys: data.active_api_keys || 0,
    };
  },

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
   * Terminate a session and return the role to the queue
   */
  terminateSession: async (sessionId: string): Promise<{
    sessionId: string;
    status: string;
    roleId: number;
    roleName: string;
    roleReturnedToQueue: boolean;
    message: string;
  }> => {
    const response = await apiClient.post(`/api/scraper-monitoring/sessions/${sessionId}/terminate`);
    return {
      sessionId: response.data.session_id,
      status: response.data.status,
      roleId: response.data.role_id,
      roleName: response.data.role_name,
      roleReturnedToQueue: response.data.role_returned_to_queue,
      message: response.data.message,
    };
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
   * Reject a pending role - permanently deletes from database
   */
  rejectRole: async (roleId: number, reason?: string): Promise<void> => {
    await apiClient.post(`/api/roles/${roleId}/reject`, { reason });
  },

  /**
   * Delete a role from database (only if no candidates linked)
   */
  deleteRole: async (roleId: number): Promise<void> => {
    await apiClient.delete(`/api/roles/${roleId}`);
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
  getStatistics: async (): Promise<ImportStatistics> => {
    const response = await apiClient.get('/api/jobs/statistics');
    return {
      totalJobs: response.data.total_jobs,
      jobsByPlatform: response.data.jobs_by_platform,
      totalBatches: response.data.total_batches,
      recentImports: response.data.recent_imports.map(mapBatch),
      summary: mapSummary(response.data.summary || {}),
      platformHealth: mapPlatformHealth(response.data.platform_health || {}),
    };
  },
};

// ============================================================================
// Mappers (snake_case to camelCase)
// ============================================================================

function mapSession(data: Record<string, unknown>): ScrapeSession {
  return {
    id: data.id as number,
    sessionId: data.session_id as string,  // UUID for API calls
    scraperKeyId: data.scraper_key_id as number,
    scraperKeyName: (data.scraper_key_name || data.scraper_name) as string,
    globalRoleId: (data.global_role_id || data.role_id) as number,
    roleName: data.role_name as string,
    status: data.status as ScrapeSession['status'],
    jobsFound: (data.jobs_found ?? 0) as number,
    jobsImported: (data.jobs_imported ?? 0) as number,
    jobsSkipped: (data.jobs_skipped ?? 0) as number,
    platformsTotal: (data.platforms_total ?? 0) as number,
    platformsCompleted: (data.platforms_completed ?? 0) as number,
    platformsFailed: (data.platforms_failed ?? 0) as number,
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
    candidateCount: (data.candidate_count ?? 0) as number,
    jobCount: (data.job_count ?? 0) as number,
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
    source: (data.source || 'scraper') as 'scraper' | 'manual_import',
    platform: data.platform as string | undefined,
    importStatus: data.import_status as string,
    roleName: data.role_name as string | undefined,
    scraperName: data.scraper_name as string | undefined,
    
    // Job counts
    totalJobs: (data.total_jobs || 0) as number,
    newJobs: (data.new_jobs || 0) as number,
    updatedJobs: (data.updated_jobs || 0) as number,
    skippedJobs: (data.skipped_jobs || 0) as number,
    failedJobs: (data.failed_jobs || 0) as number,
    
    // Platform summary
    platformsTotal: (data.platforms_total || 0) as number,
    platformsCompleted: (data.platforms_completed || 0) as number,
    platformsFailed: (data.platforms_failed || 0) as number,
    platformsPending: (data.platforms_pending || 0) as number,
    
    // Timing
    startedAt: data.started_at as string,
    completedAt: data.completed_at as string | null,
    durationSeconds: data.duration_seconds as number | null,
    durationFormatted: data.duration_formatted as string | null,
    
    // Error info
    errorMessage: data.error_message as string | null,
    sessionNotes: data.session_notes as string | null,
    
    // Platform breakdown
    platforms: ((data.platforms as Record<string, unknown>[]) || []).map(mapPlatformStatus),
  };
}

function mapPlatformStatus(data: Record<string, unknown>): PlatformStatus {
  return {
    platformName: data.platform_name as string,
    status: data.status as PlatformStatus['status'],
    statusLabel: data.status_label as string,
    jobsFound: (data.jobs_found || 0) as number,
    jobsImported: (data.jobs_imported || 0) as number,
    jobsSkipped: (data.jobs_skipped || 0) as number,
    errorMessage: data.error_message as string | null,
    startedAt: data.started_at as string | null,
    completedAt: data.completed_at as string | null,
    durationSeconds: data.duration_seconds as number | null,
    durationFormatted: data.duration_formatted as string | null,
  };
}

function mapSummary(data: Record<string, unknown>): ImportStatsSummary {
  return {
    totalSessions: (data.total_sessions || 0) as number,
    successfulSessions: (data.successful_sessions || 0) as number,
    failedSessions: (data.failed_sessions || 0) as number,
    inProgressSessions: (data.in_progress_sessions || 0) as number,
    timeoutSessions: (data.timeout_sessions || 0) as number,
    successRate: (data.success_rate || 0) as number,
    totalJobsImported: (data.total_jobs_imported || 0) as number,
    totalJobsSkipped: (data.total_jobs_skipped || 0) as number,
    totalJobsFound: (data.total_jobs_found || 0) as number,
    avgJobsPerSession: (data.avg_jobs_per_session || 0) as number,
    avgDurationSeconds: (data.avg_duration_seconds || 0) as number,
  };
}

function mapPlatformHealth(data: Record<string, Record<string, unknown>>): Record<string, PlatformHealth> {
  const result: Record<string, PlatformHealth> = {};
  for (const [platform, health] of Object.entries(data)) {
    result[platform] = {
      totalAttempts: (health.total_attempts || 0) as number,
      successful: (health.successful || 0) as number,
      failed: (health.failed || 0) as number,
      successRate: (health.success_rate || 0) as number,
      jobsImported: (health.jobs_imported || 0) as number,
      jobsSkipped: (health.jobs_skipped || 0) as number,
      avgDurationSeconds: (health.avg_duration_seconds || 0) as number,
    };
  }
  return result;
}

// ============================================================================
// Scraper Platform Types
// ============================================================================

export interface ScraperPlatform {
  id: number;
  name: string;
  displayName: string;
  baseUrl: string;
  isActive: boolean;
  priority: number;
  description: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreatePlatformRequest {
  name: string;
  display_name: string;
  base_url?: string;
  is_active?: boolean;
  priority?: number;
  description?: string;
}

export interface UpdatePlatformRequest {
  display_name?: string;
  base_url?: string;
  is_active?: boolean;
  priority?: number;
  description?: string;
}

// ============================================================================
// Scraper Platform API
// ============================================================================

function mapPlatform(data: Record<string, unknown>): ScraperPlatform {
  return {
    id: data.id as number,
    name: data.name as string,
    displayName: data.display_name as string,
    baseUrl: data.base_url as string,
    isActive: data.is_active as boolean,
    priority: data.priority as number,
    description: data.description as string | null,
    createdAt: data.created_at as string,
    updatedAt: data.updated_at as string,
  };
}

export const scraperPlatformApi = {
  /**
   * Get all scraper platforms
   */
  getPlatforms: async (): Promise<ScraperPlatform[]> => {
    const response = await apiClient.get('/api/scraper/platforms');
    return response.data.platforms.map(mapPlatform);
  },

  /**
   * Get active scraper platforms only
   */
  getActivePlatforms: async (): Promise<ScraperPlatform[]> => {
    const response = await apiClient.get('/api/scraper/platforms/active');
    return response.data.platforms.map(mapPlatform);
  },

  /**
   * Get a single platform by ID
   */
  getPlatform: async (platformId: number): Promise<ScraperPlatform> => {
    const response = await apiClient.get(`/api/scraper/platforms/${platformId}`);
    return mapPlatform(response.data.platform);
  },

  /**
   * Create a new scraper platform
   */
  createPlatform: async (data: CreatePlatformRequest): Promise<ScraperPlatform> => {
    const response = await apiClient.post('/api/scraper/platforms', data);
    return mapPlatform(response.data.platform);
  },

  /**
   * Update an existing platform
   */
  updatePlatform: async (platformId: number, data: UpdatePlatformRequest): Promise<ScraperPlatform> => {
    const response = await apiClient.put(`/api/scraper/platforms/${platformId}`, data);
    return mapPlatform(response.data.platform);
  },

  /**
   * Delete a platform
   */
  deletePlatform: async (platformId: number): Promise<void> => {
    await apiClient.delete(`/api/scraper/platforms/${platformId}`);
  },

  /**
   * Toggle platform active status
   */
  togglePlatform: async (platformId: number, isActive: boolean): Promise<ScraperPlatform> => {
    const response = await apiClient.put(`/api/scraper/platforms/${platformId}`, {
      is_active: isActive,
    });
    return mapPlatform(response.data.platform);
  },

  /**
   * Get platform statistics
   */
  getStats: async (): Promise<{
    total: number;
    active: number;
    inactive: number;
    byPlatform: Record<string, { sessions: number; jobs: number }>;
  }> => {
    const response = await apiClient.get('/api/scraper/platforms/stats');
    return response.data;
  },
};
