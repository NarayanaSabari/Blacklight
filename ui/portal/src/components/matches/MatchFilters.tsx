/**
 * MatchFilters Component
 * Provides filtering controls for job matches list
 */

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import type { JobMatchFilters } from '@/types';

interface MatchFiltersProps {
  filters: JobMatchFilters;
  onFiltersChange: (filters: JobMatchFilters) => void;
  onReset?: () => void;
}

const GRADE_OPTIONS = [
  { value: 'all', label: 'All Grades' },
  { value: 'A+', label: 'A+ (90%+ Excellent)' },
  { value: 'A', label: 'A (80-89% Great)' },
  { value: 'B+', label: 'B+ (75-79% Very Good)' },
  { value: 'B', label: 'B (70-74% Good)' },
  { value: 'C+', label: 'C+ (65-69% Fair)' },
  { value: 'C', label: 'C (<65% Minimum)' },
];

const SCORE_RANGES = [
  { value: 'all', label: 'All Scores', min: undefined, max: undefined },
  { value: '90-100', label: '90-100% (A+ Excellent)', min: 90, max: 100 },
  { value: '80-89', label: '80-89% (A Great)', min: 80, max: 89 },
  { value: '75-79', label: '75-79% (B+ Very Good)', min: 75, max: 79 },
  { value: '70-74', label: '70-74% (B Good)', min: 70, max: 74 },
  { value: '65-69', label: '65-69% (C+ Fair)', min: 65, max: 69 },
  { value: '0-64', label: '<65% (C Minimum)', min: 0, max: 64 },
];

const SORT_OPTIONS = [
  { value: 'match_score', label: 'Match Score' },
  { value: 'match_date', label: 'Match Date' },
];

export function MatchFilters({ filters, onFiltersChange, onReset }: MatchFiltersProps) {
  const handleGradeChange = (grade: string) => {
    onFiltersChange({
      ...filters,
      grade: grade === 'all' ? undefined : grade,
      page: 1,
    });
  };

  const handleScoreRangeChange = (rangeValue: string) => {
    const range = SCORE_RANGES.find((r) => r.value === rangeValue);
    onFiltersChange({
      ...filters,
      min_score: range?.min,
      max_score: range?.max,
      page: 1,
    });
  };

  const handleSortChange = (sortBy: string) => {
    onFiltersChange({
      ...filters,
      sort_by: sortBy as 'match_score' | 'match_date',
      page: 1,
    });
  };

  const handleSortOrderChange = (order: string) => {
    onFiltersChange({
      ...filters,
      sort_order: order as 'asc' | 'desc',
      page: 1,
    });
  };

  const hasActiveFilters =
    filters.grade ||
    filters.min_score !== undefined ||
    filters.max_score !== undefined;

  const getCurrentScoreRange = () => {
    const range = SCORE_RANGES.find(
      (r) => r.min === filters.min_score && r.max === filters.max_score
    );
    return range?.value || 'all';
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        {/* Grade Filter */}
        <div className="flex-1 min-w-[200px]">
          <Select
            value={filters.grade || 'all'}
            onValueChange={handleGradeChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="Filter by grade" />
            </SelectTrigger>
            <SelectContent>
              {GRADE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Score Range Filter */}
        <div className="flex-1 min-w-[200px]">
          <Select
            value={getCurrentScoreRange()}
            onValueChange={handleScoreRangeChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="Filter by score" />
            </SelectTrigger>
            <SelectContent>
              {SCORE_RANGES.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Sort By */}
        <div className="flex-1 min-w-[180px]">
          <Select
            value={filters.sort_by || 'match_score'}
            onValueChange={handleSortChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Sort Order */}
        <div className="w-[120px]">
          <Select
            value={filters.sort_order || 'desc'}
            onValueChange={handleSortOrderChange}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="desc">High to Low</SelectItem>
              <SelectItem value="asc">Low to High</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Reset Button */}
        {hasActiveFilters && onReset && (
          <Button variant="outline" onClick={onReset} size="icon">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
