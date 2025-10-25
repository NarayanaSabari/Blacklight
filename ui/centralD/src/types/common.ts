/**
 * Common TypeScript types used across the application
 */

export interface PaginationParams {
  page?: number;
  per_page?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ErrorResponse {
  error: string;
  message: string;
  status: number;
  details?: Record<string, unknown>;
}

export interface SuccessResponse<T = unknown> {
  message: string;
  data?: T;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ErrorResponse;
}

export interface DateRange {
  start_date?: string;
  end_date?: string;
}

export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface FilterParams extends PaginationParams, SortParams {
  search?: string;
}

// Loading states
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// Generic table column definition
export interface TableColumn<T> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
}

// Generic form field states
export interface FormFieldState<T> {
  value: T;
  error?: string;
  touched: boolean;
  dirty: boolean;
}

// Toast notification types
export type ToastVariant = 'default' | 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

// Audit log (for future use)
export interface AuditLog {
  id: number;
  user_id: number;
  user_type: 'PM_ADMIN' | 'PORTAL_USER';
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'LOGOUT';
  entity_type: string;
  entity_id?: number;
  changes?: Record<string, unknown>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface AuditLogFilterParams extends FilterParams {
  user_id?: number;
  user_type?: 'PM_ADMIN' | 'PORTAL_USER';
  action?: string;
  entity_type?: string;
  start_date?: string;
  end_date?: string;
}
