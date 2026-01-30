/**
 * Candidate Validation Schemas
 * 
 * Zod schemas for validating candidate data on the frontend.
 * Matches backend CandidateUpdateSchema validation rules.
 */

import { z } from 'zod';

// Education schema
export const educationSchema = z.object({
    degree: z.string().min(1, 'Degree is required'),
    field_of_study: z.string().optional().nullable(),
    institution: z.string().min(1, 'Institution is required'),
    graduation_year: z.number().int().min(1950).max(2050).optional().nullable(),
    gpa: z.number().min(0).optional().nullable(),
});

// Work Experience schema
export const workExperienceSchema = z.object({
    title: z.string().min(1, 'Job title is required'),
    company: z.string().min(1, 'Company is required'),
    location: z.string().optional().nullable(),
    start_date: z.string().optional().nullable(), // Format: YYYY-MM
    end_date: z.string().optional().nullable(), // Format: YYYY-MM or 'Present'
    is_current: z.boolean(),
    description: z.string().optional().nullable(),
    duration_months: z.number().int().optional().nullable(),
});

// Status enum matching backend
const candidateStatusSchema = z.enum([
    'processing',
    'pending_review',
    'new',
    'screening',
    'interviewed',
    'offered',
    'hired',
    'rejected',
    'withdrawn',
    'onboarded',
    'ready_for_assignment',
]);

// Main candidate update schema
export const candidateUpdateSchema = z.object({
    // Basic Info
    first_name: z.string().min(1, 'First name is required').max(100).optional(),
    last_name: z.string().max(100).optional(),
    email: z.string().email('Invalid email address').optional().nullable().or(z.literal('')),
    phone: z.string().max(20).optional(),
    full_name: z.string().max(200).optional(),

    // Contact Info
    location: z.string().max(200).optional(),
    linkedin_url: z.string().max(500).optional().nullable(),
    portfolio_url: z.string().max(500).optional().nullable(),

    // Professional Info
    current_title: z.string().max(200).optional(),
    total_experience_years: z
        .number()
        .int('Experience must be a whole number')
        .min(0, 'Experience cannot be negative')
        .max(70, 'Experience cannot exceed 70 years')
        .optional()
        .nullable(),
    notice_period: z.string().max(100).optional(),
    expected_salary: z.string().max(100).optional(),
    visa_type: z.string().max(50).optional(),
    professional_summary: z.string().optional(),

    // Arrays
    preferred_locations: z.array(z.string()).optional(),
    skills: z.array(z.string()).optional(),
    certifications: z.array(z.string()).optional(),
    languages: z.array(z.string()).optional(),

    // JSONB data
    education: z.array(educationSchema).optional(),
    work_experience: z.array(workExperienceSchema).optional(),

    // Metadata
    status: candidateStatusSchema.optional(),
    source: z.string().max(100).optional(),
});

// Infer types from schemas
export type CandidateUpdateInput = z.infer<typeof candidateUpdateSchema>;
export type EducationInput = z.infer<typeof educationSchema>;
export type WorkExperienceInput = z.infer<typeof workExperienceSchema>;
