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
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { X, Plus, Trash2, Briefcase, GraduationCap } from 'lucide-react';
import type { Candidate, CandidateCreateInput, CandidateUpdateInput, CandidateStatus } from '@/types/candidate';

interface WorkExperience {
  title: string;
  company: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  is_current?: boolean;
  description?: string;
  duration_months?: number;
}

interface Education {
  degree: string;
  field_of_study?: string;
  institution: string;
  graduation_year?: number;
  gpa?: number;
}

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
    status: 'new',
    source: 'manual',
  });

  const [skillInput, setSkillInput] = useState('');
  const [certInput, setCertInput] = useState('');
  const [langInput, setLangInput] = useState('');
  const [locInput, setLocInput] = useState('');

  // Work experience and education state
  const [workExperience, setWorkExperience] = useState<WorkExperience[]>([]);
  const [education, setEducation] = useState<Education[]>([]);

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
        education: candidate.education,
        work_experience: candidate.work_experience,
        status: candidate.status,
        source: candidate.source,
      });
      
      // Initialize work experience and education
      setWorkExperience(candidate.work_experience || []);
      setEducation(candidate.education || []);
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
        status: 'new',
        source: 'resume_upload',
      });
      
      // Initialize work experience and education from parsed data
      setWorkExperience((parsedData.work_experience as WorkExperience[]) || []);
      setEducation((parsedData.education as Education[]) || []);
    }
  }, [candidate, parsedData]);

  const handleInputChange = (field: keyof CandidateCreateInput, value: string | number | undefined) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const addSkill = () => {
    if (skillInput.trim()) {
      setFormData((prev) => ({
        ...prev,
        skills: [...(prev.skills || []), skillInput.trim()],
      }));
      setSkillInput('');
    }
  };

  const removeSkill = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      skills: prev.skills?.filter((_, i) => i !== index),
    }));
  };

  const addCertification = () => {
    if (certInput.trim()) {
      setFormData((prev) => ({
        ...prev,
        certifications: [...(prev.certifications || []), certInput.trim()],
      }));
      setCertInput('');
    }
  };

  const removeCertification = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      certifications: prev.certifications?.filter((_, i) => i !== index),
    }));
  };

  const addLanguage = () => {
    if (langInput.trim()) {
      setFormData((prev) => ({
        ...prev,
        languages: [...(prev.languages || []), langInput.trim()],
      }));
      setLangInput('');
    }
  };

  const removeLanguage = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      languages: prev.languages?.filter((_, i) => i !== index),
    }));
  };

  const addPreferredLocation = () => {
    if (locInput.trim()) {
      setFormData((prev) => ({
        ...prev,
        preferred_locations: [...(prev.preferred_locations || []), locInput.trim()],
      }));
      setLocInput('');
    }
  };

  const removePreferredLocation = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      preferred_locations: prev.preferred_locations?.filter((_, i) => i !== index),
    }));
  };

  // Work Experience handlers
  const addWorkExperience = () => {
    setWorkExperience([...workExperience, {
      title: '',
      company: '',
      location: '',
      start_date: '',
      end_date: '',
      is_current: false,
      description: '',
    }]);
  };

  const updateWorkExperience = (index: number, field: keyof WorkExperience, value: string | boolean | number | undefined) => {
    const updated = [...workExperience];
    updated[index] = { ...updated[index], [field]: value };
    setWorkExperience(updated);
  };

  const removeWorkExperience = (index: number) => {
    setWorkExperience(workExperience.filter((_, i) => i !== index));
  };

  // Education handlers
  const addEducation = () => {
    setEducation([...education, {
      degree: '',
      field_of_study: '',
      institution: '',
      graduation_year: undefined,
      gpa: undefined,
    }]);
  };

  const updateEducation = (index: number, field: keyof Education, value: string | number | undefined) => {
    const updated = [...education];
    updated[index] = { ...updated[index], [field]: value };
    setEducation(updated);
  };

  const removeEducation = (index: number) => {
    setEducation(education.filter((_, i) => i !== index));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Include work experience and education in submission
    // Ensure is_current always has a boolean value
    const submitData = {
      ...formData,
      work_experience: workExperience.map(exp => ({
        ...exp,
        is_current: exp.is_current || false,
      })),
      education: education,
    };
    
    onSubmit(submitData);
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
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="last_name">Last Name *</Label>
            <Input
              id="last_name"
              value={formData.last_name}
              onChange={(e) => handleInputChange('last_name', e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={formData.email || ''}
              onChange={(e) => handleInputChange('email', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input
              id="phone"
              type="tel"
              value={formData.phone || ''}
              onChange={(e) => handleInputChange('phone', e.target.value)}
            />
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
              value={formData.total_experience_years || ''}
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
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="portfolio_url">Portfolio/Website</Label>
            <Input
              id="portfolio_url"
              type="url"
              value={formData.portfolio_url || ''}
              onChange={(e) => handleInputChange('portfolio_url', e.target.value)}
              placeholder="https://portfolio.com"
            />
          </div>
        </div>
      </div>

      {/* Skills */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Skills</h3>
        
        <div className="flex gap-2">
          <Input
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill())}
            placeholder="Add a skill..."
          />
          <Button type="button" onClick={addSkill} variant="outline" size="icon">
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {formData.skills?.map((skill, index) => (
            <Badge key={index} variant="secondary" className="gap-1">
              {skill}
              <button
                type="button"
                onClick={() => removeSkill(index)}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      </div>

      {/* Certifications */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Certifications</h3>
        
        <div className="flex gap-2">
          <Input
            value={certInput}
            onChange={(e) => setCertInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCertification())}
            placeholder="Add a certification..."
          />
          <Button type="button" onClick={addCertification} variant="outline" size="icon">
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {formData.certifications?.map((cert, index) => (
            <Badge key={index} variant="secondary" className="gap-1">
              {cert}
              <button
                type="button"
                onClick={() => removeCertification(index)}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      </div>

      {/* Languages */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Languages</h3>
        
        <div className="flex gap-2">
          <Input
            value={langInput}
            onChange={(e) => setLangInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addLanguage())}
            placeholder="Add a language..."
          />
          <Button type="button" onClick={addLanguage} variant="outline" size="icon">
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {formData.languages?.map((lang, index) => (
            <Badge key={index} variant="secondary" className="gap-1">
              {lang}
              <button
                type="button"
                onClick={() => removeLanguage(index)}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      </div>

      {/* Preferred Locations */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-900">Preferred Work Locations</h3>
        
        <div className="flex gap-2">
          <Input
            value={locInput}
            onChange={(e) => setLocInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addPreferredLocation())}
            placeholder="Add a preferred location..."
          />
          <Button type="button" onClick={addPreferredLocation} variant="outline" size="icon">
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {formData.preferred_locations?.map((loc, index) => (
            <Badge key={index} variant="secondary" className="gap-1">
              {loc}
              <button
                type="button"
                onClick={() => removePreferredLocation(index)}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      </div>

      {/* Work Experience */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Briefcase className="h-5 w-5" />
            Work Experience
          </h3>
          <Button type="button" onClick={addWorkExperience} variant="outline" size="sm" className="gap-2">
            <Plus className="h-4 w-4" />
            Add Experience
          </Button>
        </div>

        {workExperience.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8 border-2 border-dashed rounded-lg">
            No work experience added yet. Click "Add Experience" to get started.
          </p>
        ) : (
          <div className="space-y-4">
            {workExperience.map((exp, index) => (
              <Card key={index}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">Experience #{index + 1}</CardTitle>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeWorkExperience(index)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Job Title *</Label>
                      <Input
                        value={exp.title}
                        onChange={(e) => updateWorkExperience(index, 'title', e.target.value)}
                        placeholder="e.g., Senior Software Engineer"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Company *</Label>
                      <Input
                        value={exp.company}
                        onChange={(e) => updateWorkExperience(index, 'company', e.target.value)}
                        placeholder="e.g., Google"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Location</Label>
                      <Input
                        value={exp.location || ''}
                        onChange={(e) => updateWorkExperience(index, 'location', e.target.value)}
                        placeholder="e.g., San Francisco, CA"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Start Date</Label>
                      <Input
                        type="month"
                        value={exp.start_date || ''}
                        onChange={(e) => updateWorkExperience(index, 'start_date', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>End Date</Label>
                      <Input
                        type="month"
                        value={exp.end_date || ''}
                        onChange={(e) => updateWorkExperience(index, 'end_date', e.target.value)}
                        disabled={exp.is_current}
                      />
                    </div>
                    <div className="space-y-2 flex items-end">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={exp.is_current || false}
                          onChange={(e) => {
                            updateWorkExperience(index, 'is_current', e.target.checked);
                            if (e.target.checked) {
                              updateWorkExperience(index, 'end_date', '');
                            }
                          }}
                          className="h-4 w-4"
                        />
                        <span className="text-sm font-medium">Current Position</span>
                      </label>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Description</Label>
                    <Textarea
                      value={exp.description || ''}
                      onChange={(e) => updateWorkExperience(index, 'description', e.target.value)}
                      rows={4}
                      placeholder="Describe your responsibilities and achievements..."
                    />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Education */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <GraduationCap className="h-5 w-5" />
            Education
          </h3>
          <Button type="button" onClick={addEducation} variant="outline" size="sm" className="gap-2">
            <Plus className="h-4 w-4" />
            Add Education
          </Button>
        </div>

        {education.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8 border-2 border-dashed rounded-lg">
            No education added yet. Click "Add Education" to get started.
          </p>
        ) : (
          <div className="space-y-4">
            {education.map((edu, index) => (
              <Card key={index}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">Education #{index + 1}</CardTitle>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeEducation(index)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Degree *</Label>
                      <Input
                        value={edu.degree}
                        onChange={(e) => updateEducation(index, 'degree', e.target.value)}
                        placeholder="e.g., Bachelor of Science"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Field of Study</Label>
                      <Input
                        value={edu.field_of_study || ''}
                        onChange={(e) => updateEducation(index, 'field_of_study', e.target.value)}
                        placeholder="e.g., Computer Science"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Institution *</Label>
                      <Input
                        value={edu.institution}
                        onChange={(e) => updateEducation(index, 'institution', e.target.value)}
                        placeholder="e.g., MIT"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Graduation Year</Label>
                      <Input
                        type="number"
                        min="1950"
                        max="2050"
                        value={edu.graduation_year || ''}
                        onChange={(e) => updateEducation(index, 'graduation_year', e.target.value ? parseInt(e.target.value) : undefined)}
                        placeholder="e.g., 2020"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>GPA</Label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        max="4"
                        value={edu.gpa || ''}
                        onChange={(e) => updateEducation(index, 'gpa', e.target.value ? parseFloat(e.target.value) : undefined)}
                        placeholder="e.g., 3.8"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
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
