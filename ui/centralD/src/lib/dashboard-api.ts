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
  location: string | null;  // Location for location-specific scraping
  roleLocationQueueId: number | null;  // Reference to role_location_queue entry
  status: 'in_progress' | 'completed' | 'failed' | 'terminated';
  jobsFound: number;
  jobsImported: number;
  jobsSkipped: number;
  platformsTotal: number;
  platformsCompleted: number;
  platformsFailed: number;
  // Batch progress tracking for real-time monitoring
  totalBatches: number;
  completedBatches: number;
  startedAt: string;
  completedAt: string | null;
  updatedAt: string | null;  // Last update timestamp for activity tracking
  errorMessage: string | null;
  durationSeconds: number | null;
}

export interface SessionDetails extends ScrapeSession {
  platformStatuses: SessionPlatformStatus[];
}

// Platform status for session details (includes id)
export interface SessionPlatformStatus {
  id: number;
  platformName: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  jobsFound: number;
  jobsImported: number;
  jobsSkipped: number;
  // Batch progress tracking for platforms with large job lists
  totalBatches: number;
  completedBatches: number;
  startedAt: string | null;
  completedAt: string | null;
  updatedAt: string | null;
  durationSeconds: number | null;
  errorMessage: string | null;
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

export interface LocationStats {
  location: string;
  jobsFound: number;
  jobsImported: number;
  sessionCount: number;
}

export interface LocationAnalytics {
  sessionsWithLocation: number;
  sessionsWithoutLocation: number;
  topLocations: LocationStats[];
  queue: {
    total: number;
    pending: number;
    approved: number;
    processing: number;
    completed: number;
    uniqueLocations: number;
  };
}

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
  locationAnalytics: LocationAnalytics;
}

export const scraperMonitoringApi = {
  /**
   * Get scraper statistics
   */
  getStats: async (): Promise<ScraperStats> => {
    const response = await apiClient.get('/api/scraper-monitoring/stats');
    const data = response.data;
    const locationData = data.location_analytics || {};
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
      locationAnalytics: {
        sessionsWithLocation: locationData.sessions_with_location || 0,
        sessionsWithoutLocation: locationData.sessions_without_location || 0,
        topLocations: (locationData.top_locations || []).map((loc: Record<string, unknown>) => ({
          location: loc.location as string,
          jobsFound: (loc.jobs_found ?? 0) as number,
          jobsImported: (loc.jobs_imported ?? 0) as number,
          sessionCount: (loc.session_count ?? 0) as number,
        })),
        queue: {
          total: locationData.queue?.total || 0,
          pending: locationData.queue?.pending || 0,
          approved: locationData.queue?.approved || 0,
          processing: locationData.queue?.processing || 0,
          completed: locationData.queue?.completed || 0,
          uniqueLocations: locationData.queue?.unique_locations || 0,
        },
      },
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

  /**
   * Get detailed session information including platform statuses
   */
  getSessionDetails: async (sessionId: string): Promise<SessionDetails> => {
    const response = await apiClient.get(`/api/scraper-monitoring/sessions/${sessionId}`);
    const data = response.data;
    
    // Map platform statuses
    const platformStatuses: SessionPlatformStatus[] = (data.platform_statuses || []).map(
      (ps: Record<string, unknown>) => ({
        id: ps.id as number,
        platformName: ps.platform_name as string,
        status: ps.status as SessionPlatformStatus['status'],
        jobsFound: (ps.jobs_found ?? 0) as number,
        jobsImported: (ps.jobs_imported ?? 0) as number,
        jobsSkipped: (ps.jobs_skipped ?? 0) as number,
        totalBatches: (ps.total_batches ?? 1) as number,
        completedBatches: (ps.completed_batches ?? 0) as number,
        startedAt: ps.started_at as string | null,
        completedAt: ps.completed_at as string | null,
        updatedAt: ps.updated_at as string | null,
        durationSeconds: ps.duration_seconds as number | null,
        errorMessage: ps.error_message as string | null,
      })
    );
    
    return {
      ...mapSession(data),
      platformStatuses,
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
    location: (data.location as string | null) || null,  // Location for location-specific scraping
    roleLocationQueueId: (data.role_location_queue_id as number | null) || null,
    status: data.status as ScrapeSession['status'],
    jobsFound: (data.jobs_found ?? 0) as number,
    jobsImported: (data.jobs_imported ?? 0) as number,
    jobsSkipped: (data.jobs_skipped ?? 0) as number,
    platformsTotal: (data.platforms_total ?? 0) as number,
    platformsCompleted: (data.platforms_completed ?? 0) as number,
    platformsFailed: (data.platforms_failed ?? 0) as number,
    // Batch progress tracking
    totalBatches: (data.total_batches ?? 0) as number,
    completedBatches: (data.completed_batches ?? 0) as number,
    startedAt: data.started_at as string,
    completedAt: data.completed_at as string | null,
    updatedAt: data.updated_at as string | null,
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

// ============================================================================
// Job Postings Types
// ============================================================================

export interface JobPosting {
  id: number;
  externalJobId: string;
  platform: string;
  title: string;
  company: string;
  location: string | null;
  salaryRange: string | null;
  salaryMin: number | null;
  salaryMax: number | null;
  salaryCurrency: string | null;
  snippet: string | null;
  description?: string;
  requirements: string | null;
  postedDate: string | null;
  expiresAt: string | null;
  jobType: string | null;
  isRemote: boolean;
  experienceRequired: string | null;
  experienceMin: number | null;
  experienceMax: number | null;
  skills: string[] | null;
  keywords: string[] | null;
  jobUrl: string;
  applyUrl: string | null;
  status: string;
  importedAt: string | null;
  createdAt: string;
  updatedAt: string;
  scraperName?: string;
  roleName?: string;
}

export interface JobListResponse {
  jobs: JobPosting[];
  total: number;
  page: number;
  perPage: number;
  pages: number;
  filters: {
    platforms: string[];
    statuses: string[];
    locations?: string[];
  };
}

export interface JobStatistics {
  totalJobs: number;
  jobsByPlatform: Record<string, number>;
  jobsByStatus: Record<string, number>;
  remoteJobs: number;
  uniqueCompanies: number;
  jobsToday: number;
  jobsThisWeek: number;
}

export interface JobListParams {
  page?: number;
  perPage?: number;
  search?: string;
  platform?: string;
  location?: string;
  status?: string;
  isRemote?: boolean;
  roleId?: number;
  sortBy?: 'created_at' | 'posted_date' | 'title' | 'company' | 'salary_min';
  sortOrder?: 'asc' | 'desc';
}

// ============================================================================
// Job Postings API
// ============================================================================

function mapJobPosting(data: Record<string, unknown>): JobPosting {
  return {
    id: data.id as number,
    externalJobId: data.external_job_id as string,
    platform: data.platform as string,
    title: data.title as string,
    company: data.company as string,
    location: data.location as string | null,
    salaryRange: data.salary_range as string | null,
    salaryMin: data.salary_min as number | null,
    salaryMax: data.salary_max as number | null,
    salaryCurrency: data.salary_currency as string | null,
    snippet: data.snippet as string | null,
    description: data.description as string | undefined,
    requirements: data.requirements as string | null,
    postedDate: data.posted_date as string | null,
    expiresAt: data.expires_at as string | null,
    jobType: data.job_type as string | null,
    isRemote: data.is_remote as boolean,
    experienceRequired: data.experience_required as string | null,
    experienceMin: data.experience_min as number | null,
    experienceMax: data.experience_max as number | null,
    skills: data.skills as string[] | null,
    keywords: data.keywords as string[] | null,
    jobUrl: data.job_url as string,
    applyUrl: data.apply_url as string | null,
    status: data.status as string,
    importedAt: data.imported_at as string | null,
    createdAt: data.created_at as string,
    updatedAt: data.updated_at as string,
    scraperName: data.scraper_name as string | undefined,
    roleName: data.role_name as string | undefined,
  };
}

export const jobPostingsApi = {
  /**
   * List all job postings with filters and pagination
   */
  listJobs: async (params: JobListParams = {}): Promise<JobListResponse> => {
    const queryParams = new URLSearchParams();
    
    if (params.page) queryParams.set('page', params.page.toString());
    if (params.perPage) queryParams.set('per_page', params.perPage.toString());
    if (params.search) queryParams.set('search', params.search);
    if (params.platform) queryParams.set('platform', params.platform);
    if (params.location) queryParams.set('location', params.location);
    if (params.status) queryParams.set('status', params.status);
    if (params.isRemote !== undefined) queryParams.set('is_remote', params.isRemote.toString());
    if (params.roleId) queryParams.set('role_id', params.roleId.toString());
    if (params.sortBy) queryParams.set('sort_by', params.sortBy);
    if (params.sortOrder) queryParams.set('sort_order', params.sortOrder);
    
    const response = await apiClient.get(`/api/scraper-monitoring/jobs?${queryParams.toString()}`);
    
    return {
      jobs: response.data.jobs.map(mapJobPosting),
      total: response.data.total,
      page: response.data.page,
      perPage: response.data.per_page,
      pages: response.data.pages,
      filters: response.data.filters,
    };
  },

  /**
   * Get a single job posting by ID
   */
  getJob: async (jobId: number): Promise<JobPosting> => {
    const response = await apiClient.get(`/api/scraper-monitoring/jobs/${jobId}`);
    return mapJobPosting(response.data);
  },

  /**
   * Get job statistics
   */
  getStatistics: async (): Promise<JobStatistics> => {
    const response = await apiClient.get('/api/scraper-monitoring/jobs/statistics');
    return {
      totalJobs: response.data.total_jobs,
      jobsByPlatform: response.data.jobs_by_platform,
      jobsByStatus: response.data.jobs_by_status,
      remoteJobs: response.data.remote_jobs,
      uniqueCompanies: response.data.unique_companies,
      jobsToday: response.data.jobs_today,
      jobsThisWeek: response.data.jobs_this_week,
    };
  },
};

// ============================================================================
// Role Location Queue Types
// ============================================================================

export interface RoleLocationQueueEntry {
  id: number;
  globalRoleId: number;
  roleName: string | null;
  location: string;
  queueStatus: 'pending' | 'approved' | 'processing' | 'completed' | 'rejected';
  priority: 'urgent' | 'high' | 'normal' | 'low';
  candidateCount: number;
  totalJobsScraped: number;
  lastScrapedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface RoleLocationQueueListResponse {
  entries: RoleLocationQueueEntry[];
  total: number;
  page: number;
  perPage: number;
  stats: {
    byStatus: Record<string, number>;
    totalEntries: number;
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapRoleLocationQueueEntry(data: any): RoleLocationQueueEntry {
  return {
    id: data.id,
    globalRoleId: data.global_role_id,
    roleName: data.role_name,
    location: data.location,
    queueStatus: data.queue_status,
    priority: data.priority,
    candidateCount: data.candidate_count || 0,
    totalJobsScraped: data.total_jobs_scraped || 0,
    lastScrapedAt: data.last_scraped_at,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}

// ============================================================================
// Role Location Queue API
// ============================================================================

export const roleLocationQueueApi = {
  /**
   * Get role+location queue entries
   */
  getEntries: async (params?: {
    status?: string;
    search?: string;
    page?: number;
    perPage?: number;
  }): Promise<RoleLocationQueueListResponse> => {
    const queryParams = new URLSearchParams();
    
    if (params?.status && params.status !== 'all') {
      queryParams.set('status', params.status);
    }
    if (params?.search) queryParams.set('search', params.search);
    if (params?.page) queryParams.set('page', params.page.toString());
    if (params?.perPage) queryParams.set('per_page', params.perPage.toString());
    
    const response = await apiClient.get(
      `/api/scraper-monitoring/role-location-queue?${queryParams.toString()}`
    );
    
    return {
      entries: response.data.entries.map(mapRoleLocationQueueEntry),
      total: response.data.total,
      page: response.data.page,
      perPage: response.data.per_page,
      stats: {
        byStatus: response.data.stats.by_status,
        totalEntries: response.data.stats.total_entries,
      },
    };
  },

  /**
   * Approve a role+location queue entry
   */
  approveEntry: async (entryId: number): Promise<RoleLocationQueueEntry> => {
    const response = await apiClient.post(
      `/api/scraper-monitoring/role-location-queue/${entryId}/approve`
    );
    return mapRoleLocationQueueEntry(response.data.entry);
  },

  /**
   * Reject a role+location queue entry
   */
  rejectEntry: async (entryId: number): Promise<RoleLocationQueueEntry> => {
    const response = await apiClient.post(
      `/api/scraper-monitoring/role-location-queue/${entryId}/reject`
    );
    return mapRoleLocationQueueEntry(response.data.entry);
  },

  /**
   * Update priority of a role+location queue entry
   */
  updatePriority: async (
    entryId: number,
    priority: string
  ): Promise<RoleLocationQueueEntry> => {
    const response = await apiClient.patch(
      `/api/scraper-monitoring/role-location-queue/${entryId}/priority`,
      { priority }
    );
    return mapRoleLocationQueueEntry(response.data.entry);
  },

  /**
   * Delete a role+location queue entry
   */
  deleteEntry: async (entryId: number): Promise<void> => {
    await apiClient.delete(
      `/api/scraper-monitoring/role-location-queue/${entryId}`
    );
  },

  /**
   * Bulk approve pending entries
   */
  bulkApprove: async (entryIds?: number[]): Promise<{ approvedCount: number }> => {
    const response = await apiClient.post(
      '/api/scraper-monitoring/role-location-queue/bulk-approve',
      { entry_ids: entryIds }
    );
    return { approvedCount: response.data.approved_count };
  },

  /**
   * Get all locations for a specific role
   */
  getLocationsForRole: async (roleId: number): Promise<{
    roleId: number;
    roleName: string;
    locations: Array<{
      id: number;
      location: string;
      queueStatus: string;
      priority: string;
      candidateCount: number;
      totalJobsScraped: number;
      lastScrapedAt: string | null;
    }>;
    totalLocations: number;
  }> => {
    const response = await apiClient.get(
      `/api/scraper-monitoring/role-location-queue/by-role/${roleId}`
    );
    return {
      roleId: response.data.role_id,
      roleName: response.data.role_name,
      locations: response.data.locations.map((loc: {
        id: number;
        location: string;
        queue_status: string;
        priority: string;
        candidate_count: number;
        total_jobs_scraped: number;
        last_scraped_at: string | null;
      }) => ({
        id: loc.id,
        location: loc.location,
        queueStatus: loc.queue_status,
        priority: loc.priority,
        candidateCount: loc.candidate_count,
        totalJobsScraped: loc.total_jobs_scraped,
        lastScrapedAt: loc.last_scraped_at,
      })),
      totalLocations: response.data.total_locations,
    };
  },
};

// ============================================================================
// Session Job Logs Types
// ============================================================================

export interface SessionJobLog {
  id: number;
  sessionId: string;
  platformName: string;
  jobIndex: number;
  externalJobId: string | null;
  title: string | null;
  company: string | null;
  location: string | null;
  status: 'pending' | 'imported' | 'skipped' | 'error';
  importedJobId: number | null;
  skipReason: string | null;
  skipReasonDetail: string | null;
  duplicateJobId: number | null;
  errorMessage: string | null;
  processedAt: string | null;
  createdAt: string | null;
  rawJobData?: Record<string, unknown>;
  duplicateJob?: {
    id: number;
    title: string;
    company: string;
    location: string;
    platform: string;
    externalJobId: string;
    description: string;
    postedDate: string | null;
    createdAt: string | null;
    jobUrl: string;
  };
}

export interface SessionJobLogSummary {
  total: number;
  imported: number;
  skipped: number;
  error: number;
  pending: number;
  skipReasons: {
    duplicate_platform_id: number;
    duplicate_title_company_location: number;
    duplicate_title_company_description: number;
    missing_required: number;
    error: number;
  };
  byPlatform: Record<string, {
    total: number;
    imported: number;
    skipped: number;
    error: number;
  }>;
}

export interface SessionJobLogsResponse {
  sessionId: string;
  sessionInfo: {
    sessionId: string;
    roleName: string;
    location: string | null;
    status: string;
    scraperName: string;
    startedAt: string | null;
    completedAt: string | null;
    durationSeconds: number | null;
    platformsTotal: number;
    platformsCompleted: number;
    platformsFailed: number;
    jobsFound: number;
    jobsImported: number;
    jobsSkipped: number;
  };
  summary: SessionJobLogSummary;
  jobs: SessionJobLog[];
  pagination: {
    page: number;
    perPage: number;
    total: number;
    pages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface SessionJobLogDetailResponse {
  jobLog: SessionJobLog;
  rawJobData: Record<string, unknown>;
  duplicateJob?: {
    id: number;
    title: string;
    company: string;
    location: string;
    description: string;
    platform: string;
    externalJobId: string;
    jobUrl: string;
    postedDate: string | null;
    createdAt: string | null;
    skills: string[];
    salaryRange: string | null;
    experienceRequired: string | null;
    isRemote: boolean;
  };
  importedJob?: {
    id: number;
    title: string;
    company: string;
    location: string;
    platform: string;
    externalJobId: string;
    jobUrl: string;
    createdAt: string | null;
  };
  comparison?: {
    title: { incoming: string; existing: string; match: boolean };
    company: { incoming: string; existing: string; match: boolean };
    location: { incoming: string; existing: string; match: boolean };
    platform: { incoming: string; existing: string; match: boolean };
    externalId: { incoming: string; existing: string; match: boolean };
    descriptionPreview: { incoming: string; existing: string; match: boolean };
  };
}

export interface SessionSummaryResponse {
  sessionInfo: {
    sessionId: string;
    roleName: string;
    location: string | null;
    status: string;
    scraperName: string;
    startedAt: string | null;
    completedAt: string | null;
    durationSeconds: number | null;
  };
  summary: SessionJobLogSummary;
  platformBreakdown: Array<{
    platformName: string;
    status: string;
    jobsFound: number;
    jobsImported: number;
    jobsSkipped: number;
    errorMessage: string | null;
    completedAt: string | null;
  }>;
  skipReasonsChart: Array<{
    reason: string;
    count: number;
  }>;
}

// ============================================================================
// Session Job Logs API
// ============================================================================

const mapSessionJobLog = (data: Record<string, unknown>): SessionJobLog => ({
  id: data.id as number,
  sessionId: data.session_id as string,
  platformName: data.platform_name as string,
  jobIndex: data.job_index as number,
  externalJobId: data.external_job_id as string | null,
  title: data.title as string | null,
  company: data.company as string | null,
  location: data.location as string | null,
  status: data.status as SessionJobLog['status'],
  importedJobId: data.imported_job_id as number | null,
  skipReason: data.skip_reason as string | null,
  skipReasonDetail: data.skip_reason_detail as string | null,
  duplicateJobId: data.duplicate_job_id as number | null,
  errorMessage: data.error_message as string | null,
  processedAt: data.processed_at as string | null,
  createdAt: data.created_at as string | null,
  rawJobData: data.raw_job_data as Record<string, unknown> | undefined,
  duplicateJob: data.duplicate_job ? {
    id: (data.duplicate_job as Record<string, unknown>).id as number,
    title: (data.duplicate_job as Record<string, unknown>).title as string,
    company: (data.duplicate_job as Record<string, unknown>).company as string,
    location: (data.duplicate_job as Record<string, unknown>).location as string,
    platform: (data.duplicate_job as Record<string, unknown>).platform as string,
    externalJobId: (data.duplicate_job as Record<string, unknown>).external_job_id as string,
    description: (data.duplicate_job as Record<string, unknown>).description as string,
    postedDate: (data.duplicate_job as Record<string, unknown>).posted_date as string | null,
    createdAt: (data.duplicate_job as Record<string, unknown>).created_at as string | null,
    jobUrl: (data.duplicate_job as Record<string, unknown>).job_url as string,
  } : undefined,
});

export const sessionJobLogsApi = {
  /**
   * Get job logs for a session with pagination and filtering
   */
  getSessionJobLogs: async (
    sessionId: string,
    params?: {
      status?: 'all' | 'imported' | 'skipped' | 'error';
      skipReason?: string;
      page?: number;
      perPage?: number;
      includeRawData?: boolean;
      includeDuplicate?: boolean;
    }
  ): Promise<SessionJobLogsResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.skipReason) queryParams.append('skip_reason', params.skipReason);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.perPage) queryParams.append('per_page', params.perPage.toString());
    if (params?.includeRawData !== undefined) queryParams.append('include_raw_data', params.includeRawData.toString());
    if (params?.includeDuplicate !== undefined) queryParams.append('include_duplicate', params.includeDuplicate.toString());

    const response = await apiClient.get(
      `/api/scraper-monitoring/sessions/${sessionId}/jobs?${queryParams.toString()}`
    );

    return {
      sessionId: response.data.session_id,
      sessionInfo: {
        sessionId: response.data.session_info.session_id,
        roleName: response.data.session_info.role_name,
        location: response.data.session_info.location,
        status: response.data.session_info.status,
        scraperName: response.data.session_info.scraper_name,
        startedAt: response.data.session_info.started_at,
        completedAt: response.data.session_info.completed_at,
        durationSeconds: response.data.session_info.duration_seconds,
        platformsTotal: response.data.session_info.platforms_total,
        platformsCompleted: response.data.session_info.platforms_completed,
        platformsFailed: response.data.session_info.platforms_failed,
        jobsFound: response.data.session_info.jobs_found,
        jobsImported: response.data.session_info.jobs_imported,
        jobsSkipped: response.data.session_info.jobs_skipped,
      },
      summary: {
        total: response.data.summary.total,
        imported: response.data.summary.imported,
        skipped: response.data.summary.skipped,
        error: response.data.summary.error,
        pending: response.data.summary.pending,
        skipReasons: response.data.summary.skip_reasons,
        byPlatform: response.data.summary.by_platform,
      },
      jobs: response.data.jobs.map(mapSessionJobLog),
      pagination: {
        page: response.data.pagination.page,
        perPage: response.data.pagination.per_page,
        total: response.data.pagination.total,
        pages: response.data.pagination.pages,
        hasNext: response.data.pagination.has_next,
        hasPrev: response.data.pagination.has_prev,
      },
    };
  },

  /**
   * Get detailed information for a single job log
   */
  getJobLogDetail: async (
    sessionId: string,
    jobLogId: number
  ): Promise<SessionJobLogDetailResponse> => {
    const response = await apiClient.get(
      `/api/scraper-monitoring/sessions/${sessionId}/jobs/${jobLogId}`
    );

    return {
      jobLog: mapSessionJobLog(response.data.job_log),
      rawJobData: response.data.raw_job_data,
      duplicateJob: response.data.duplicate_job ? {
        id: response.data.duplicate_job.id,
        title: response.data.duplicate_job.title,
        company: response.data.duplicate_job.company,
        location: response.data.duplicate_job.location,
        description: response.data.duplicate_job.description,
        platform: response.data.duplicate_job.platform,
        externalJobId: response.data.duplicate_job.external_job_id,
        jobUrl: response.data.duplicate_job.job_url,
        postedDate: response.data.duplicate_job.posted_date,
        createdAt: response.data.duplicate_job.created_at,
        skills: response.data.duplicate_job.skills,
        salaryRange: response.data.duplicate_job.salary_range,
        experienceRequired: response.data.duplicate_job.experience_required,
        isRemote: response.data.duplicate_job.is_remote,
      } : undefined,
      importedJob: response.data.imported_job ? {
        id: response.data.imported_job.id,
        title: response.data.imported_job.title,
        company: response.data.imported_job.company,
        location: response.data.imported_job.location,
        platform: response.data.imported_job.platform,
        externalJobId: response.data.imported_job.external_job_id,
        jobUrl: response.data.imported_job.job_url,
        createdAt: response.data.imported_job.created_at,
      } : undefined,
      comparison: response.data.comparison ? {
        title: response.data.comparison.title,
        company: response.data.comparison.company,
        location: response.data.comparison.location,
        platform: response.data.comparison.platform,
        externalId: response.data.comparison.external_id,
        descriptionPreview: response.data.comparison.description_preview,
      } : undefined,
    };
  },

  /**
   * Get session summary with skip reasons chart
   */
  getSessionSummary: async (sessionId: string): Promise<SessionSummaryResponse> => {
    const response = await apiClient.get(
      `/api/scraper-monitoring/sessions/${sessionId}/summary`
    );

    return {
      sessionInfo: {
        sessionId: response.data.session_info.session_id,
        roleName: response.data.session_info.role_name,
        location: response.data.session_info.location,
        status: response.data.session_info.status,
        scraperName: response.data.session_info.scraper_name,
        startedAt: response.data.session_info.started_at,
        completedAt: response.data.session_info.completed_at,
        durationSeconds: response.data.session_info.duration_seconds,
      },
      summary: {
        total: response.data.summary.total,
        imported: response.data.summary.imported,
        skipped: response.data.summary.skipped,
        error: response.data.summary.error,
        pending: response.data.summary.pending,
        skipReasons: response.data.summary.skip_reasons,
        byPlatform: response.data.summary.by_platform,
      },
      platformBreakdown: response.data.platform_breakdown.map((p: Record<string, unknown>) => ({
        platformName: p.platform_name as string,
        status: p.status as string,
        jobsFound: p.jobs_found as number,
        jobsImported: p.jobs_imported as number,
        jobsSkipped: p.jobs_skipped as number,
        errorMessage: p.error_message as string | null,
        completedAt: p.completed_at as string | null,
      })),
      skipReasonsChart: response.data.skip_reasons_chart,
    };
  },
};

// ============================================================================
// SCRAPER CREDENTIALS API
// ============================================================================

export type CredentialPlatform = 'linkedin' | 'glassdoor' | 'techfetch';
export type CredentialStatus = 'available' | 'in_use' | 'failed' | 'disabled' | 'cooldown';

export interface ScraperCredential {
  id: number;
  platform: CredentialPlatform;
  name: string;
  email: string | null;
  status: CredentialStatus;
  notes: string | null;
  failureCount: number;
  successCount: number;
  lastFailureAt: string | null;
  lastFailureMessage: string | null;
  lastSuccessAt: string | null;
  assignedToSessionId: string | null;
  assignedAt: string | null;
  cooldownUntil: string | null;
  createdAt: string;
  updatedAt: string;
  // Only included when include_credentials=true
  password?: string;
  jsonCredentials?: Record<string, unknown>;
}

export interface CredentialStats {
  platform: string;
  total: number;
  available: number;
  inUse: number;
  failed: number;
  disabled: number;
  cooldown: number;
  totalSuccesses: number;
  totalFailures: number;
}

export interface AllCredentialStats {
  linkedin: CredentialStats;
  glassdoor: CredentialStats;
  techfetch: CredentialStats;
}

// Helper function to map API response to camelCase
function mapCredential(data: Record<string, unknown>): ScraperCredential {
  return {
    id: data.id as number,
    platform: data.platform as CredentialPlatform,
    name: data.name as string,
    email: data.email as string | null,
    status: data.status as CredentialStatus,
    notes: data.notes as string | null,
    failureCount: data.failure_count as number,
    successCount: data.success_count as number,
    lastFailureAt: data.last_failure_at as string | null,
    lastFailureMessage: data.last_failure_message as string | null,
    lastSuccessAt: data.last_success_at as string | null,
    assignedToSessionId: data.assigned_to_session_id as string | null,
    assignedAt: data.assigned_at as string | null,
    cooldownUntil: data.cooldown_until as string | null,
    createdAt: data.created_at as string,
    updatedAt: data.updated_at as string,
    password: data.password as string | undefined,
    jsonCredentials: data.json_credentials as Record<string, unknown> | undefined,
  };
}

function mapStats(data: Record<string, unknown>): CredentialStats {
  return {
    platform: data.platform as string,
    total: data.total as number,
    available: data.available as number,
    inUse: data.in_use as number,
    failed: data.failed as number,
    disabled: data.disabled as number,
    cooldown: data.cooldown as number,
    totalSuccesses: data.total_successes as number,
    totalFailures: data.total_failures as number,
  };
}

export const scraperCredentialsApi = {
  /**
   * Get all credentials with optional filters
   */
  getAll: async (params?: { platform?: string; status?: string }): Promise<{
    credentials: ScraperCredential[];
    total: number;
  }> => {
    const queryParams = new URLSearchParams();
    if (params?.platform) queryParams.set('platform', params.platform);
    if (params?.status) queryParams.set('status', params.status);

    const response = await apiClient.get(
      `/api/scraper-credentials/?${queryParams.toString()}`
    );

    return {
      credentials: (response.data.credentials as Record<string, unknown>[]).map(mapCredential),
      total: response.data.total,
    };
  },

  /**
   * Get stats for all platforms
   */
  getAllStats: async (): Promise<AllCredentialStats> => {
    const response = await apiClient.get('/api/scraper-credentials/stats');

    return {
      linkedin: mapStats(response.data.linkedin),
      glassdoor: mapStats(response.data.glassdoor),
      techfetch: mapStats(response.data.techfetch),
    };
  },

  /**
   * Get credentials for a specific platform
   */
  getByPlatform: async (
    platform: CredentialPlatform,
    status?: string
  ): Promise<{
    platform: string;
    credentials: ScraperCredential[];
    stats: CredentialStats;
  }> => {
    const queryParams = new URLSearchParams();
    if (status) queryParams.set('status', status);

    const response = await apiClient.get(
      `/api/scraper-credentials/platforms/${platform}?${queryParams.toString()}`
    );

    return {
      platform: response.data.platform,
      credentials: (response.data.credentials as Record<string, unknown>[]).map(mapCredential),
      stats: mapStats(response.data.stats),
    };
  },

  /**
   * Get a single credential by ID
   */
  getById: async (
    id: number,
    includeCredentials = false
  ): Promise<ScraperCredential> => {
    const response = await apiClient.get(
      `/api/scraper-credentials/${id}?include_credentials=${includeCredentials}`
    );
    return mapCredential(response.data.credential);
  },

  /**
   * Create a new email/password credential (LinkedIn, Techfetch)
   */
  createEmailCredential: async (data: {
    platform: 'linkedin' | 'techfetch';
    name: string;
    email: string;
    password: string;
    notes?: string;
  }): Promise<ScraperCredential> => {
    const response = await apiClient.post('/api/scraper-credentials/', data);
    return mapCredential(response.data.credential);
  },

  /**
   * Create a new JSON credential (Glassdoor)
   */
  createJsonCredential: async (data: {
    platform: 'glassdoor';
    name: string;
    json_credentials: Record<string, unknown>;
    notes?: string;
  }): Promise<ScraperCredential> => {
    const response = await apiClient.post('/api/scraper-credentials/', data);
    return mapCredential(response.data.credential);
  },

  /**
   * Update a credential
   */
  update: async (
    id: number,
    data: {
      name?: string;
      email?: string;
      password?: string;
      json_credentials?: Record<string, unknown>;
      notes?: string;
    }
  ): Promise<ScraperCredential> => {
    const response = await apiClient.put(`/api/scraper-credentials/${id}`, data);
    return mapCredential(response.data.credential);
  },

  /**
   * Delete a credential
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/scraper-credentials/${id}`);
  },

  /**
   * Enable a credential (make available)
   */
  enable: async (id: number): Promise<ScraperCredential> => {
    const response = await apiClient.post(`/api/scraper-credentials/${id}/enable`);
    return mapCredential(response.data.credential);
  },

  /**
   * Disable a credential
   */
  disable: async (id: number): Promise<ScraperCredential> => {
    const response = await apiClient.post(`/api/scraper-credentials/${id}/disable`);
    return mapCredential(response.data.credential);
  },

  /**
   * Reset a failed credential
   */
  reset: async (id: number): Promise<ScraperCredential> => {
    const response = await apiClient.post(`/api/scraper-credentials/${id}/reset`);
    return mapCredential(response.data.credential);
  },
};

// ============================================================================
// Subscription Plans API
// ============================================================================

import type { 
  SubscriptionPlan, 
  SubscriptionPlanListResponse,
  CustomPlanCreateRequest,
  CustomPlanUpdateRequest,
} from '@/types/subscription-plan';

export const subscriptionPlansApi = {
  /**
   * List all subscription plans (standard plans only for global view)
   */
  list: async (params?: {
    page?: number;
    per_page?: number;
    include_inactive?: boolean;
  }): Promise<SubscriptionPlanListResponse> => {
    const response = await apiClient.get('/api/subscription-plans', { params });
    return response.data;
  },

  /**
   * Get a single subscription plan by ID
   */
  get: async (planId: number): Promise<SubscriptionPlan> => {
    const response = await apiClient.get(`/api/subscription-plans/${planId}`);
    return response.data.plan;
  },

  /**
   * Get available plans for a specific tenant
   * Returns standard plans + custom plans for this tenant
   */
  listForTenant: async (
    tenantId: number,
    includeInactive: boolean = false
  ): Promise<SubscriptionPlan[]> => {
    const response = await apiClient.get(
      `/api/subscription-plans/tenants/${tenantId}/available`,
      { params: { include_inactive: includeInactive } }
    );
    return response.data.plans;
  },

  /**
   * Create a custom plan for a specific tenant
   */
  createCustom: async (data: CustomPlanCreateRequest): Promise<SubscriptionPlan> => {
    const response = await apiClient.post('/api/subscription-plans/custom', data);
    return response.data.plan;
  },

  /**
   * Update a custom plan
   */
  updateCustom: async (
    planId: number,
    data: CustomPlanUpdateRequest
  ): Promise<SubscriptionPlan> => {
    const response = await apiClient.put(`/api/subscription-plans/${planId}`, data);
    return response.data.plan;
  },

  /**
   * Delete a custom plan
   */
  deleteCustom: async (planId: number): Promise<void> => {
    await apiClient.delete(`/api/subscription-plans/${planId}`);
  },
};
