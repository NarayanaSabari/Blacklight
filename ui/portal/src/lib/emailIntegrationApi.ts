/**
 * Email Integration API
 * Handles Gmail/Outlook OAuth integrations and email jobs
 */

import { apiClient } from './api-client';

// Types
export interface EmailIntegration {
  id: number;
  provider: 'gmail' | 'outlook';
  email_address: string | null;
  is_active: boolean;
  last_synced_at: string | null;
  emails_processed_count: number;
  jobs_created_count: number;
  last_error: string | null;
  created_at: string;
}

export interface IntegrationStatus {
  gmail: {
    connected: boolean;
    is_configured: boolean;
    integration_id?: number;
    email?: string;
    is_active?: boolean;
    emails_processed?: number;
    jobs_created?: number;
    last_synced?: string | null;
    last_error?: string | null;
  };
  outlook: {
    connected: boolean;
    is_configured: boolean;
    integration_id?: number;
    email?: string;
    is_active?: boolean;
    emails_processed?: number;
    jobs_created?: number;
    last_synced?: string | null;
    last_error?: string | null;
  };
}

export interface EmailJob {
  id: number;
  external_job_id: string;
  platform: string;
  title: string;
  company: string | null;
  location: string | null;
  description: string | null;
  snippet: string | null;
  requirements: string | null;
  job_type: string | null;
  is_remote: boolean;
  skills: string[] | null;
  keywords: string[] | null;
  // Salary
  salary_range: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  // Experience
  experience_required: string | null;
  experience_min: number | null;
  experience_max: number | null;
  // Status & Dates
  status: string;
  posted_date: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string | null;
  // Email source fields
  is_email_sourced: boolean;
  source_tenant_id: number | null;
  sourced_by_user_id: number | null;
  source_email_id: string | null;
  source_email_subject: string | null;
  source_email_sender: string | null;
  source_email_date: string | null;
  // URLs
  job_url: string | null;
  apply_url: string | null;
  // Extended by route
  sourced_by?: {
    id: number;
    name: string;
    email: string;
  };
}

export interface EmailJobsResponse {
  jobs: EmailJob[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface EmailJobsStats {
  total_jobs: number;
  by_status: Record<string, number>;
  by_user: Array<{
    user_id: number;
    name: string;
    jobs_count: number;
  }>;
  emails_processed: number;
  emails_converted: number;
  conversion_rate: number;
}

export interface ProcessedEmail {
  id: number;
  integration_id: number;
  email_message_id: string;
  email_subject: string | null;
  email_sender: string | null;
  processing_result: string;
  job_id: number | null;
  skip_reason: string | null;
  parsing_confidence: number | null;
  created_at: string;
}

export interface ProcessedEmailsResponse {
  emails: ProcessedEmail[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// API Functions
export const emailIntegrationApi = {
  /**
   * Get current integration status for user
   */
  getStatus: async (): Promise<IntegrationStatus> => {
    const response = await apiClient.get('/api/integrations/email/status');
    return response.data;
  },

  /**
   * List all integrations for current user
   */
  listIntegrations: async (): Promise<EmailIntegration[]> => {
    const response = await apiClient.get('/api/integrations/email/list');
    return response.data;
  },

  /**
   * Get Gmail connection URL
   */
  connectGmail: async (): Promise<{ authorization_url: string }> => {
    const response = await apiClient.get('/api/integrations/email/connect/gmail');
    return response.data;
  },

  /**
   * Get Outlook connection URL
   */
  connectOutlook: async (): Promise<{ authorization_url: string }> => {
    const response = await apiClient.get('/api/integrations/email/connect/outlook');
    return response.data;
  },

  /**
   * Disconnect an integration
   */
  disconnect: async (integrationId: number): Promise<void> => {
    await apiClient.delete(`/api/integrations/email/${integrationId}`);
  },

  /**
   * Toggle integration active status
   */
  toggle: async (integrationId: number, isActive: boolean): Promise<EmailIntegration> => {
    const response = await apiClient.patch(`/api/integrations/email/${integrationId}/toggle`, {
      is_active: isActive,
    });
    return response.data;
  },

  /**
   * Trigger manual sync
   */
  triggerSync: async (integrationId: number): Promise<void> => {
    await apiClient.post(`/api/integrations/email/${integrationId}/sync`);
  },
};

export const emailJobsApi = {
  /**
   * List email-sourced jobs
   */
  list: async (params?: {
    page?: number;
    per_page?: number;
    sourced_by?: number;
    search?: string;
    status?: string;
  }): Promise<EmailJobsResponse> => {
    const response = await apiClient.get('/api/email-jobs', { params });
    return response.data;
  },

  /**
   * Get a single email job
   */
  get: async (jobId: number): Promise<EmailJob> => {
    const response = await apiClient.get(`/api/email-jobs/${jobId}`);
    return response.data;
  },

  /**
   * Update an email job
   */
  update: async (jobId: number, data: Partial<EmailJob>): Promise<EmailJob> => {
    const response = await apiClient.put(`/api/email-jobs/${jobId}`, data);
    return response.data;
  },

  /**
   * Delete an email job
   */
  delete: async (jobId: number): Promise<void> => {
    await apiClient.delete(`/api/email-jobs/${jobId}`);
  },

  /**
   * Get email jobs statistics
   */
  getStats: async (): Promise<EmailJobsStats> => {
    const response = await apiClient.get('/api/email-jobs/stats');
    return response.data;
  },

  /**
   * List processed emails
   */
  listProcessedEmails: async (params?: {
    page?: number;
    per_page?: number;
    result?: string;
    integration_id?: number;
  }): Promise<ProcessedEmailsResponse> => {
    const response = await apiClient.get('/api/email-jobs/emails', { params });
    return response.data;
  },
};
