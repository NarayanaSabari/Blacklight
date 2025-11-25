/**
 * Candidate Form Component
 * Editable form for candidate data with validation
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TagInput } from '@/components/ui/tag-input';
import { WorkExperienceEditor } from '@/components/candidates/WorkExperienceEditor';
import { EducationEditor } from '@/components/candidates/EducationEditor';
import { candidateUpdateSchema as candidateSchema } from '@/schemas/candidateSchema';
import { toast } from 'sonner';
import { ZodError } from 'zod';
import type { Candidate, CandidateCreateInput, CandidateUpdateInput, CandidateStatus } from '@/types/candidate';

interface CandidateFormProps {
  candidate?: Candidate; // If provided, form is in edit mode
  parsedData?: Record<string, unknown>; // Pre-filled data from resume parsing
  onSubmit: (data: CandidateCreateInput | CandidateUpdateInput) => void | Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

const STATUS_OPTIONS: { value: CandidateStatus; label: string }[] = [
  { value: 'new', label: 'New' },
  { value: 'screening', label: 'Screening' },
  { value: 'interviewed', label: 'Interviewed' },
  { value: 'offered', label: 'Offered' },
  { value: 'hired', label: 'Hired' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'withdrawn', label: 'Withdrawn' },
];

export function CandidateForm({
  candidate,
  parsedData,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: CandidateFormProps) {
  // Form state
  const [formData, setFormData] = useState<CandidateCreateInput>({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    location: '',
    linkedin_url: '',
    portfolio_url: '',
    current_title: '',
    total_experience_years: undefined,
    notice_period: '',
    expected_salary: '',
    professional_summary: '',
    skills: [],
    certifications: [],
    languages: [],
    preferred_locations: [],
    work_experience: [],
    education: [],
    status: 'new',
    source: 'manual',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Initialize form data
  useEffect(() => {
    if (candidate) {
      // Edit mode: populate from existing candidate
      setFormData({
        first_name: candidate.first_name,
        last_name: candidate.last_name,
        email: candidate.email,
        phone: candidate.phone,
        full_name: candidate.full_name,
        location: candidate.location,
        linkedin_url: candidate.linkedin_url,
        portfolio_url: candidate.portfolio_url,
        current_title: candidate.current_title,
        total_experience_years: candidate.total_experience_years,
        notice_period: candidate.notice_period,
        expected_salary: candidate.expected_salary,
        professional_summary: candidate.professional_summary,
        skills: candidate.skills || [],
        certifications: candidate.certifications || [],
        languages: candidate.languages || [],
        preferred_locations: candidate.preferred_locations || [],
        education: candidate.education || [],
        work_experience: candidate.work_experience || [],
        status: candidate.status,
        source: candidate.source,
      });
    } else if (parsedData) {
      // Create mode with parsed data: pre-fill from resume
      setFormData({
        first_name: (parsedData.full_name as string)?.split(' ')[0] || '',
        last_name: (parsedData.full_name as string)?.split(' ').slice(1).join(' ') || '',
        full_name: parsedData.full_name as string,
        email: parsedData.email as string,
        phone: parsedData.phone as string,
        location: parsedData.location as string,
        linkedin_url: parsedData.linkedin_url as string,
        portfolio_url: parsedData.portfolio_url as string,
        current_title: parsedData.current_title as string,
        total_experience_years: parsedData.total_experience_years as number,
        professional_summary: parsedData.professional_summary as string,
        skills: (parsedData.skills as string[]) || [],
        certifications: (parsedData.certifications as string[]) || [],
        languages: (parsedData.languages as string[]) || [],
        preferred_locations: (parsedData.preferred_locations as string[]) || [],
        work_experience: (parsedData.work_experience as any[]) || [],
        education: (parsedData.education as any[]) || [],
        status: 'new',
        source: 'resume_upload',
      });
    }
  }, [candidate, parsedData]);

  const handleInputChange = (field: keyof CandidateCreateInput, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    try {
      // Validate with Zod
      // We use partial validation for create since some fields might be optional in UI but required in schema
      // or vice versa depending on strictness. 
      // Ideally we should use the schema to parse.

      // Clean up empty strings to null/undefined where appropriate for numbers
      const dataToValidate = {
        ...formData,
        total_experience_years: formData.total_experience_years === '' ? null : formData.total_experience_years,
      };

      // For creation, we might need to ensure required fields are present
      // The schema handles this.
      const validatedData = candidateSchema.parse(dataToValidate);

      console.log('Form submission data:', validatedData);
      onSubmit(validatedData as CandidateCreateInput);
    } catch (error) {
      if (error instanceof ZodError) {
        const newErrors: Record<string, string> = {};
        error.errors.forEach((err) => {
          const path = err.path.join('.');
          newErrors[path] = err.message;
        });
        setErrors(newErrors);
        toast.error('Please fix the validation errors');
        console.error('Validation errors:', newErrors);
      } else {
        console.error('Form submission error:', error);
        toast.error('An unexpected error occurred');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Information */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Basic Information</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="first_name">First Name *</Label>
            <Input
              id="first_name"
              value={formData.first_name}
              onChange={(e) => handleInputChange('first_name', e.target.value)}
              className={errors.first_name ? 'border-red-500' : ''}
              required
            />
            {errors.first_name && <p className="text-xs text-red-500">{errors.first_name}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="last_name">Last Name *</Label>
            <Input
              id="last_name"
              value={formData.last_name}
              onChange={(e) => handleInputChange('last_name', e.target.value)}
              className={errors.last_name ? 'border-red-500' : ''}
              required
            />
            {errors.last_name && <p className="text-xs text-red-500">{errors.last_name}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={formData.email || ''}
              onChange={(e) => handleInputChange('email', e.target.value)}
              className={errors.email ? 'border-red-500' : ''}
            />
            {errors.email && <p className="text-xs text-red-500">{errors.email}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input
              id="phone"
              type="tel"
              value={formData.phone || ''}
              onChange={(e) => handleInputChange('phone', e.target.value)}
              className={errors.phone ? 'border-red-500' : ''}
            />
            {errors.phone && <p className="text-xs text-red-500">{errors.phone}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              value={formData.location || ''}
              onChange={(e) => handleInputChange('location', e.target.value)}
              placeholder="City, State, Country"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select
              value={formData.status}
              onValueChange={(value) => handleInputChange('status', value as CandidateStatus)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Professional Information */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Professional Information</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="current_title">Current Title</Label>
            <Input
              id="current_title"
              value={formData.current_title || ''}
              onChange={(e) => handleInputChange('current_title', e.target.value)}
              placeholder="e.g., Senior Software Engineer"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="total_experience_years">Years of Experience</Label>
            <Input
              id="total_experience_years"
              type="number"
              min="0"
              value={formData.total_experience_years ?? ''}
              onChange={(e) => handleInputChange('total_experience_years', e.target.value ? parseInt(e.target.value) : undefined)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="notice_period">Notice Period</Label>
            <Input
              id="notice_period"
              value={formData.notice_period || ''}
              onChange={(e) => handleInputChange('notice_period', e.target.value)}
              placeholder="e.g., 2 weeks, Immediate"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="expected_salary">Expected Salary</Label>
            <Input
              id="expected_salary"
              value={formData.expected_salary || ''}
              onChange={(e) => handleInputChange('expected_salary', e.target.value)}
              placeholder="e.g., $120,000 - $150,000"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="professional_summary">Professional Summary</Label>
          <Textarea
            id="professional_summary"
            value={formData.professional_summary || ''}
            onChange={(e) => handleInputChange('professional_summary', e.target.value)}
            rows={4}
            placeholder="Brief professional summary..."
          />
        </div>
      </div>

      {/* Links */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Links</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="linkedin_url">LinkedIn URL</Label>
            <Input
              id="linkedin_url"
              type="url"
              value={formData.linkedin_url || ''}
              onChange={(e) => handleInputChange('linkedin_url', e.target.value)}
              placeholder="https://linkedin.com/in/username"
              className={errors.linkedin_url ? 'border-red-500' : ''}
            />
            {errors.linkedin_url && <p className="text-xs text-red-500">{errors.linkedin_url}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="portfolio_url">Portfolio/Website</Label>
            <Input
              id="portfolio_url"
              type="url"
              value={formData.portfolio_url || ''}
              onChange={(e) => handleInputChange('portfolio_url', e.target.value)}
              placeholder="https://portfolio.com"
              className={errors.portfolio_url ? 'border-red-500' : ''}
            />
            {errors.portfolio_url && <p className="text-xs text-red-500">{errors.portfolio_url}</p>}
          </div>
        </div>
      </div>

      {/* Skills */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Skills</h3>
        <TagInput
          value={formData.skills || []}
          onChange={(skills) => handleInputChange('skills', skills)}
          placeholder="Add a skill..."
        />
      </div>

      {/* Certifications */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Certifications</h3>
        <TagInput
          value={formData.certifications || []}
          onChange={(certs) => handleInputChange('certifications', certs)}
          placeholder="Add a certification..."
        />
      </div>

      {/* Languages */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Languages</h3>
        <TagInput
          value={formData.languages || []}
          onChange={(langs) => handleInputChange('languages', langs)}
          placeholder="Add a language..."
        />
      </div>

      {/* Preferred Locations */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Preferred Work Locations</h3>
        <TagInput
          value={formData.preferred_locations || []}
          onChange={(locs) => handleInputChange('preferred_locations', locs)}
          placeholder="Add a preferred location..."
        />
      </div>

      {/* Work Experience */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Work Experience</h3>
        <WorkExperienceEditor
          value={formData.work_experience || []}
          onChange={(exp) => handleInputChange('work_experience', exp)}
        />
      </div>

      {/* Education */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Education</h3>
        <EducationEditor
          value={formData.education || []}
          onChange={(edu) => handleInputChange('education', edu)}
        />
      </div>

      {/* Form Actions */}
      <div className="flex gap-3 justify-end pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving...' : candidate ? 'Update Candidate' : 'Create Candidate'}
        </Button>
      </div>
    </form>
  );
}
