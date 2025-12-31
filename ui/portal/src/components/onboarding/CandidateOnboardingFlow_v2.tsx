/**
 * CandidateOnboardingFlow Component (v2 with AI Resume Parsing)
 * Multi-step wizard for candidate self-onboarding with AI resume parsing
 * Steps: 
 * 1) Personal Info
 * 2) Resume Upload + AI Parsing (with manual entry option)
 * 3) Review & Edit Parsed Data
 * 4) Additional Documents (Dynamic based on tenant settings)
 * 5) Final Review & Submit
 */

import { useState, useEffect } from 'react';
import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { cn } from '@/lib/utils';
import {
  Card,
  CardContent,
  CardFooter,
} from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  User,
  FileText,
  Paperclip,
  Eye,
  Loader2,
  Sparkles,
  Edit3,
  Upload,
  AlertCircle,
  AlertTriangle,
} from 'lucide-react';
import { DocumentUpload, type UploadedFile } from '@/components/documents/DocumentUpload';
import { useSubmitOnboarding, useUploadOnboardingDocument } from '@/hooks/useOnboarding';
import { onboardingApi, type DocumentRequirement } from '@/lib/api/invitationApi';
import type { InvitationWithRelations } from '@/types';
import { toast } from 'sonner';
import { TagInput } from '@/components/ui/tag-input';
import { WorkExperienceEditor } from '@/components/candidates/WorkExperienceEditor';
import { EducationEditor } from '@/components/candidates/EducationEditor';
import { Label } from '@/components/ui/label';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

const personalInfoSchema = z.object({
  first_name: z.string().min(2, 'First name must be at least 2 characters'),
  last_name: z.string().min(2, 'Last name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  phone: z.string().min(10, 'Phone number must be at least 10 digits').max(20, 'Phone number is too long'),
  location: z.string().optional(),
  linkedin_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  github_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  portfolio_url: z.string().url('Invalid URL').optional().or(z.literal('')),
});

const professionalInfoSchema = z.object({
  position: z.string().optional(),
  experience_years: z.number().min(0).max(50).optional(),
  expected_salary: z.string().min(1, 'Expected pay rate is required'),
  skills: z.string().optional(),
  education: z.string().optional(),
  work_experience: z.string().optional(),
  summary: z.string().min(50, 'Summary must be at least 50 characters').optional().or(z.literal('')),
});

type PersonalInfoValues = z.infer<typeof personalInfoSchema>;
type ProfessionalInfoValues = z.infer<typeof professionalInfoSchema>;

interface CandidateOnboardingFlowProps {
  token: string;
  invitation: InvitationWithRelations;
  onSuccess: () => void;
}

interface ParsedResumeData {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
  skills?: string[];
  experience?: string;
  education?: string;
  summary?: string;
  total_experience_years?: number;
}

export function CandidateOnboardingFlow({
  token,
  invitation,
  onSuccess,
}: CandidateOnboardingFlowProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [resumeFiles, setResumeFiles] = useState<UploadedFile[]>([]);
  const [additionalFiles, setAdditionalFiles] = useState<UploadedFile[]>([]);
  const [parsedData, setParsedData] = useState<ParsedResumeData | null>(null);
  const [originalParsedData, setOriginalParsedData] = useState<Record<string, unknown> | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [entryMethod, setEntryMethod] = useState<'upload' | 'manual'>('upload');
  const [skillTags, setSkillTags] = useState<string[]>([]);
  const [workExperience, setWorkExperience] = useState<any[]>([]);
  const [education, setEducation] = useState<any[]>([]);
  const [preferredRoles, setPreferredRoles] = useState<string[]>([]);
  const [preferredLocations, setPreferredLocations] = useState<string[]>([]);
  const [suggestedRoles, setSuggestedRoles] = useState<{
    roles: Array<{ role: string; score: number; reasoning: string }>;
    generated_at: string;
    model_version: string;
  } | null>(null);
  const [isGeneratingRoles, setIsGeneratingRoles] = useState(false);
  
  // Document requirements state
  const [documentRequirements, setDocumentRequirements] = useState<DocumentRequirement[]>([]);
  const [documentFiles, setDocumentFiles] = useState<Record<string, UploadedFile[]>>({});
  const [isLoadingRequirements, setIsLoadingRequirements] = useState(true);
  
  // Confirmation dialog state
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  
  // Success state
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [countdown, setCountdown] = useState(5);

  const submitMutation = useSubmitOnboarding();
  const uploadMutation = useUploadOnboardingDocument();

  const personalForm = useForm<PersonalInfoValues>({
    resolver: zodResolver(personalInfoSchema),
    defaultValues: {
      first_name: invitation.first_name || '',
      last_name: invitation.last_name || '',
      email: invitation.email,
      phone: '',
      location: '',
      linkedin_url: '',
      github_url: '',
      portfolio_url: '',
    },
  });

  const professionalForm = useForm<ProfessionalInfoValues>({
    resolver: zodResolver(professionalInfoSchema),
    defaultValues: {
      position: '',
      experience_years: 0,
      expected_salary: '',
      skills: '',
      education: '',
      work_experience: '',
      summary: '',
    },
  });

  const steps = [
    { number: 1, title: 'Personal Info', icon: User },
    { number: 2, title: 'Resume', icon: FileText },
    { number: 3, title: 'Review Details', icon: Edit3 },
    { number: 4, title: 'Documents', icon: Paperclip },
    { number: 5, title: 'Final Review', icon: Eye },
  ];

  const progress = (currentStep / steps.length) * 100;

  // Parse resume when file is uploaded
  const handleResumeUpload = async (files: UploadedFile[]) => {
    setResumeFiles(files);

    if (files.length > 0 && files[0].file) {
      setIsParsing(true);
      try {
        const data = await onboardingApi.parseResume(token, files[0].file);

        if (data.status === 'success' && data.parsed_data) {
          // Store ORIGINAL structured data for submission
          const apiData = data.parsed_data;
          setOriginalParsedData(apiData);

          // Format work experience as string FOR DISPLAY ONLY
          const workExpText = apiData.work_experience?.map((exp: Record<string, unknown>) =>
            `${exp.title} at ${exp.company} (${exp.start_date || ''} - ${exp.end_date || exp.is_current ? 'Present' : ''})\n${exp.description || ''}`
          ).join('\n\n') || '';

          // Format education as string FOR DISPLAY ONLY
          const educationText = apiData.education?.map((edu: Record<string, unknown>) =>
            `${edu.degree}${edu.field_of_study ? ' in ' + edu.field_of_study : ''}\n${edu.institution}\n${edu.graduation_year || ''}`
          ).join('\n\n') || '';

          const transformedData: ParsedResumeData = {
            name: apiData.full_name || undefined,
            email: apiData.email || undefined,
            phone: apiData.phone || undefined,
            location: apiData.location || undefined,
            skills: apiData.skills || [],
            experience: workExpText || undefined,
            education: educationText || undefined,
            summary: apiData.professional_summary || undefined,
            total_experience_years: apiData.total_experience_years || undefined,
          };

          setParsedData(transformedData);
          toast.success('Resume parsed successfully! Please review the extracted information.');
        } else {
          throw new Error('Invalid response format');
        }
      } catch (error) {
        console.error('Resume parsing failed:', error);
        toast.error(error instanceof Error ? error.message : 'Failed to parse resume. You can enter details manually.');
        setParsedData(null);
      } finally {
        setIsParsing(false);
      }
    }
  };

  // Fetch document requirements on mount
  useEffect(() => {
    const fetchDocumentRequirements = async () => {
      try {
        setIsLoadingRequirements(true);
        const response = await onboardingApi.getDocumentRequirements(token);
        // Sort by display_order
        const sorted = (response.requirements || []).sort(
          (a, b) => (a.display_order || 0) - (b.display_order || 0)
        );
        setDocumentRequirements(sorted);
      } catch (error) {
        console.error('Failed to fetch document requirements:', error);
        // Non-fatal - just means no custom requirements configured
        setDocumentRequirements([]);
      } finally {
        setIsLoadingRequirements(false);
      }
    };
    
    fetchDocumentRequirements();
  }, [token]);

  // Auto-fill form with parsed data when available
  useEffect(() => {
    if (parsedData && currentStep === 3) {
      // Auto-fill professional form with parsed data
      if (parsedData.skills) {
        professionalForm.setValue('skills', parsedData.skills.join(', '));
        setSkillTags(parsedData.skills);
      }
      if (parsedData.experience) {
        professionalForm.setValue('work_experience', parsedData.experience);
      }
      if (parsedData.education) {
        professionalForm.setValue('education', parsedData.education);
      }
      if (parsedData.summary) {
        professionalForm.setValue('summary', parsedData.summary);
      }
      if (parsedData.total_experience_years) {
        professionalForm.setValue('experience_years', parsedData.total_experience_years);
      }

      // Update personal info if needed
      if (parsedData.phone && !personalForm.getValues('phone')) {
        personalForm.setValue('phone', parsedData.phone);
      }
      if (parsedData.location && !personalForm.getValues('location')) {
        personalForm.setValue('location', parsedData.location);
      }

      // Initialize structured work experience / education from original parsed data when available
      if (originalParsedData && Array.isArray((originalParsedData as any).work_experience)) {
        setWorkExperience((originalParsedData as any).work_experience as any[]);
      }
      if (originalParsedData && Array.isArray((originalParsedData as any).education)) {
        setEducation((originalParsedData as any).education as any[]);
      }
      // Initialize preferred roles from parsed data if available
      if (originalParsedData?.preferred_roles && Array.isArray(originalParsedData.preferred_roles)) {
        setPreferredRoles(originalParsedData.preferred_roles as string[]);
      }
    }
  }, [parsedData, originalParsedData, currentStep, professionalForm, personalForm]);

  // Helper to get MIME types from file extensions or pass through if already MIME types
  const getMimeTypesFromExtensions = (fileTypes: string[]): string[] => {
    const mimeMap: Record<string, string> = {
      'pdf': 'application/pdf',
      'doc': 'application/msword',
      'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
      'png': 'image/png',
      'gif': 'image/gif',
      'txt': 'text/plain',
    };
    return fileTypes.map(ft => {
      // If it's already a MIME type (contains /), pass through
      if (ft.includes('/')) {
        return ft;
      }
      // Otherwise, map extension to MIME type
      return mimeMap[ft.toLowerCase()] || `application/${ft}`;
    }).filter(Boolean);
  };

  // Helper to get friendly labels for file types (extensions or MIME types)
  const getFileTypeLabels = (fileTypes: string[]): string => {
    const mimeToLabel: Record<string, string> = {
      'application/pdf': 'PDF',
      'application/msword': 'DOC',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
      'image/jpeg': 'JPEG',
      'image/png': 'PNG',
      'image/gif': 'GIF',
      'text/plain': 'TXT',
    };
    return fileTypes.map(ft => {
      // If it's a MIME type, look up label
      if (ft.includes('/')) {
        return mimeToLabel[ft.toLowerCase()] || ft.split('/')[1]?.toUpperCase() || ft;
      }
      // Otherwise, it's an extension - just uppercase it
      return ft.toUpperCase();
    }).join(', ');
  };

  // Handle document file change for a specific requirement
  const handleDocumentFileChange = (documentType: string, files: UploadedFile[]) => {
    setDocumentFiles(prev => ({
      ...prev,
      [documentType]: files
    }));
  };

  // Check if all required documents are uploaded
  const validateRequiredDocuments = (): { valid: boolean; missing: string[] } => {
    const missing: string[] = [];
    for (const req of documentRequirements) {
      if (req.is_required) {
        const files = documentFiles[req.document_type] || [];
        if (files.length === 0) {
          missing.push(req.label);
        }
      }
    }
    return { valid: missing.length === 0, missing };
  };

  const handleNextStep = async () => {
    if (currentStep === 1) {
      const isValid = await personalForm.trigger();
      if (!isValid) return;
    }

    if (currentStep === 2) {
      if (entryMethod === 'upload' && resumeFiles.length === 0) {
        toast.error('Please upload your resume or switch to manual entry');
        return;
      }
      // If manual entry selected, skip to step 3 without parsing
      if (entryMethod === 'manual') {
        setParsedData(null);
      }
    }

    if (currentStep === 3) {
      // Validate professional form
      const isValid = await professionalForm.trigger();
      if (!isValid) return;
    }

    if (currentStep === 4) {
      // Validate required documents are uploaded
      const { valid, missing } = validateRequiredDocuments();
      if (!valid) {
        toast.error(`Please upload required documents: ${missing.join(', ')}`);
        return;
      }
    }

    setCurrentStep((prev) => Math.min(prev + 1, steps.length));
  };

  const handlePrevStep = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleGenerateRoleSuggestions = async () => {
    // Check if we have enough data
    const hasSkills = skillTags.length > 0;
    const hasExperience = workExperience.length > 0;
    const hasTitle = professionalForm.getValues('position');

    if (!hasSkills && !hasExperience && !hasTitle) {
      toast.error('Please add skills, work experience, or job title to generate suggestions');
      return;
    }

    setIsGeneratingRoles(true);
    try {
      const response = await onboardingApi.generateRoleSuggestions(token, {
        skills: skillTags,
        work_experience: workExperience,
        current_title: professionalForm.getValues('position'),
        experience_years: professionalForm.getValues('experience_years'),
      });

      setSuggestedRoles(response.suggested_roles);
      toast.success('AI role suggestions generated!');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to generate suggestions');
    } finally {
      setIsGeneratingRoles(false);
    }
  };

  const handleSubmit = async () => {
    const personalData = personalForm.getValues();
    const professionalData = professionalForm.getValues();

    try {
      // Upload resume first if uploaded
      if (resumeFiles.length > 0) {
        for (const file of resumeFiles) {
          if (file.status === 'pending') {
            await uploadMutation.mutateAsync({
              token,
              file: file.file,
              documentType: 'resume',
            });
          }
        }
      }

      // Upload required/optional documents from document requirements
      for (const [documentType, files] of Object.entries(documentFiles)) {
        for (const file of files) {
          if (file.status === 'pending') {
            await uploadMutation.mutateAsync({
              token,
              file: file.file,
              documentType,
            });
          }
        }
      }

      // Upload additional documents (legacy - for any files not in requirements)
      for (const file of additionalFiles) {
        if (file.status === 'pending') {
          await uploadMutation.mutateAsync({
            token,
            file: file.file,
            documentType: file.documentType || 'other',
          });
        }
      }

      // Resolve skills: prefer structured tags, fallback to comma-separated text
      const skills =
        skillTags.length > 0
          ? skillTags
          : professionalData.skills
            ? professionalData.skills.split(',').map((s) => s.trim())
            : undefined;

      // Merge structured data into parsed_resume_data so backend can keep rich structure
      const mergedParsed: Record<string, unknown> = {
        ...(originalParsedData || {}),
      };
      if (skills && skills.length > 0) {
        mergedParsed.skills = skills;
      }
      if (workExperience && workExperience.length > 0) {
        mergedParsed.work_experience = workExperience;
      }
      if (education && education.length > 0) {
        mergedParsed.education = education;
      }
      if (preferredRoles && preferredRoles.length > 0) {
        mergedParsed.preferred_roles = preferredRoles;
      }
      if (preferredLocations && preferredLocations.length > 0) {
        mergedParsed.preferred_locations = preferredLocations;
      }
      // Include AI suggestions if generated
      if (suggestedRoles) {
        mergedParsed.suggested_roles = suggestedRoles;
      }


      await submitMutation.mutateAsync({
        token,
        data: {
          ...personalData,
          position: professionalData.position,
          experience_years: professionalData.experience_years,
          expected_salary: professionalData.expected_salary,
          skills,
          preferred_roles: preferredRoles,
          preferred_locations: preferredLocations,
          education: professionalData.education,
          work_experience: professionalData.work_experience,
          summary: professionalData.summary,
          parsed_resume_data: Object.keys(mergedParsed).length > 0 ? mergedParsed : undefined,
        },
      });

      // Show success screen
      setShowConfirmDialog(false);
      setIsSubmitted(true);
    } catch (error) {
      console.error('Onboarding submission failed:', error);
      setShowConfirmDialog(false);
    }
  };
  
  // Countdown effect for auto-close after submission
  useEffect(() => {
    if (!isSubmitted) return;
    
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      // Close the page/tab
      window.close();
      // Fallback: if window.close() doesn't work (e.g., page wasn't opened by script)
      // redirect or call onSuccess
      onSuccess();
    }
  }, [isSubmitted, countdown, onSuccess]);

  const isSubmitting = submitMutation.isPending || uploadMutation.isPending;

  // Show success screen after submission
  if (isSubmitted) {
    return (
      <div className="mx-auto max-w-2xl">
        <Card className="border-0 shadow-xl overflow-hidden">
          {/* Success header banner */}
          <div className="bg-gradient-to-r from-green-500 to-emerald-600 p-6 text-white text-center">
            <div className="inline-flex items-center justify-center rounded-full bg-white/20 p-4 mb-4">
              <CheckCircle2 className="h-12 w-12" />
            </div>
            <h2 className="text-2xl font-bold mb-1">Application Submitted!</h2>
            <p className="text-green-100">Your profile is now under review</p>
          </div>

          <CardContent className="pt-8 pb-10">
            <div className="flex flex-col items-center text-center">
              {/* What happens next */}
              <h3 className="text-lg font-semibold text-slate-900 mb-6">What happens next?</h3>
              
              <div className="w-full max-w-sm space-y-4 text-left">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-sm font-bold text-blue-600">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Confirmation Email</p>
                    <p className="text-sm text-slate-600">
                      Check your inbox at <strong>{invitation.email}</strong>
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-sm font-bold text-blue-600">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Profile Review</p>
                    <p className="text-sm text-slate-600">Our team will review your application (2-3 days)</p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-sm font-bold text-blue-600">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Decision Notification</p>
                    <p className="text-sm text-slate-600">We'll email you with the outcome</p>
                  </div>
                </div>
              </div>

              {/* Countdown - more subtle */}
              <div className="mt-8 text-center">
                <p className="text-sm text-slate-500 mb-2">
                  This page will close in {countdown}s
                </p>
                <Button 
                  onClick={() => {
                    window.close();
                    onSuccess();
                  }}
                  className="bg-slate-900 hover:bg-slate-800"
                >
                  Close & Finish
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex gap-6 max-w-7xl mx-auto">
      {/* Side Navigation */}
      <nav className="w-72 flex-shrink-0">
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden sticky top-4">
          <div className="p-4 border-b bg-slate-50">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
              Application Progress
            </h2>
            <div className="mt-2">
              <div className="text-2xl font-bold text-slate-900">{Math.round(progress)}%</div>
              <Progress value={progress} className="h-2 mt-2" />
            </div>
          </div>
          <div className="p-2">
            {steps.map((step) => {
              const isActive = step.number === currentStep;
              const isCompleted = step.number < currentStep;
              const Icon = step.icon;
              
              return (
                <button
                  key={step.number}
                  onClick={() => {
                    // Allow navigation to completed steps or current step only
                    if (step.number <= currentStep) {
                      setCurrentStep(step.number);
                    }
                  }}
                  disabled={step.number > currentStep}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-all duration-150 group",
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : isCompleted
                        ? "text-slate-600 hover:bg-slate-50"
                        : "text-slate-400 cursor-not-allowed"
                  )}
                >
                  <div className={cn(
                    "p-2 rounded-lg transition-colors",
                    isActive 
                      ? "bg-blue-100" 
                      : isCompleted
                        ? "bg-green-100"
                        : "bg-slate-100"
                  )}>
                    {isCompleted ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <Icon className={cn(
                        "h-4 w-4",
                        isActive ? "text-blue-600" : isCompleted ? "text-green-600" : "text-slate-400"
                      )} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={cn(
                      "font-medium text-sm",
                      isActive ? "text-blue-700" : isCompleted ? "text-slate-900" : "text-slate-400"
                    )}>
                      {step.title}
                    </div>
                    <div className={cn(
                      "text-xs",
                      isActive ? "text-blue-600" : isCompleted ? "text-green-600" : "text-slate-400"
                    )}>
                      {isCompleted ? 'Completed' : isActive ? 'In Progress' : 'Pending'}
                    </div>
                  </div>
                  {isActive && (
                    <ChevronRight className="h-4 w-4 text-blue-500" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Help Card */}
        <div className="mt-4 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
          <h3 className="font-semibold text-slate-900 mb-1">Need Help?</h3>
          <p className="text-sm text-slate-600 mb-3">
            Having trouble? Contact us for assistance.
          </p>
          <a 
            href={`mailto:${invitation.email}`}
            className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
          >
            Contact Support
          </a>
        </div>
      </nav>

      {/* Content Area */}
      <div className="flex-1 min-w-0">
        <Card className="border-0 shadow-lg">
          <div className="p-4 border-b bg-slate-50">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg",
                currentStep === 1 ? "bg-blue-100" :
                currentStep === 2 ? "bg-purple-100" :
                currentStep === 3 ? "bg-green-100" :
                currentStep === 4 ? "bg-amber-100" :
                "bg-blue-100"
              )}>
                {React.createElement(steps[currentStep - 1].icon, {
                  className: cn(
                    "h-5 w-5",
                    currentStep === 1 ? "text-blue-600" :
                    currentStep === 2 ? "text-purple-600" :
                    currentStep === 3 ? "text-green-600" :
                    currentStep === 4 ? "text-amber-600" :
                    "text-blue-600"
                  )
                })}
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  {steps[currentStep - 1].title}
                </h2>
                <p className="text-sm text-slate-500">
                  Step {currentStep} of {steps.length}
                </p>
              </div>
            </div>
          </div>

          <CardContent className="p-6 md:p-8">{/* Step Content */}
          {/* Step 1: Personal Info */}
          {currentStep === 1 && (
            <Form {...personalForm}>
              <form className="space-y-8">
                {/* Section: Name */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 rounded-lg bg-blue-100">
                      <User className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">Basic Information</h3>
                      <p className="text-sm text-slate-500">Your name and contact details</p>
                    </div>
                  </div>
                  
                  <div className="grid gap-4 md:grid-cols-2">
                    <FormField
                      control={personalForm.control}
                      name="first_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>First Name <span className="text-red-500">*</span></FormLabel>
                          <FormControl>
                            <Input placeholder="John" className="h-11" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={personalForm.control}
                      name="last_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Last Name <span className="text-red-500">*</span></FormLabel>
                          <FormControl>
                            <Input placeholder="Doe" className="h-11" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <FormField
                      control={personalForm.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Email <span className="text-red-500">*</span></FormLabel>
                          <FormControl>
                            <Input 
                              type="email" 
                              placeholder="john@example.com" 
                              className="h-11 bg-slate-50" 
                              {...field} 
                              disabled 
                            />
                          </FormControl>
                          <FormDescription className="text-xs">
                            This is the email your invitation was sent to
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={personalForm.control}
                      name="phone"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Phone Number <span className="text-red-500">*</span></FormLabel>
                          <FormControl>
                            <Input placeholder="+1 (555) 123-4567" className="h-11" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={personalForm.control}
                    name="location"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Location</FormLabel>
                        <FormControl>
                          <Input placeholder="City, State or Country" className="h-11" {...field} />
                        </FormControl>
                        <FormDescription className="text-xs">
                          Where are you currently based?
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* Section: Online Profiles */}
                <div className="pt-6 border-t">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 rounded-lg bg-slate-100">
                      <Paperclip className="h-5 w-5 text-slate-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">Online Profiles</h3>
                      <p className="text-sm text-slate-500">Optional - help us learn more about you</p>
                    </div>
                  </div>
                  
                  <div className="space-y-4 bg-slate-50 rounded-lg p-4">
                    <FormField
                      control={personalForm.control}
                      name="linkedin_url"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-slate-700">LinkedIn Profile</FormLabel>
                          <FormControl>
                            <Input 
                              placeholder="https://linkedin.com/in/your-profile" 
                              className="h-11 bg-white" 
                              {...field} 
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={personalForm.control}
                      name="github_url"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-slate-700">GitHub Profile</FormLabel>
                          <FormControl>
                            <Input 
                              placeholder="https://github.com/your-username" 
                              className="h-11 bg-white" 
                              {...field} 
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={personalForm.control}
                      name="portfolio_url"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-slate-700">Portfolio / Personal Website</FormLabel>
                          <FormControl>
                            <Input 
                              placeholder="https://your-portfolio.com" 
                              className="h-11 bg-white" 
                              {...field} 
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>
              </form>
            </Form>
          )}

          {/* Step 2: Resume Upload with AI Parsing or Manual Entry */}
          {currentStep === 2 && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-100">
                  <FileText className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Your Resume</h3>
                  <p className="text-sm text-slate-500">
                    Upload your resume for AI-powered parsing or enter details manually
                  </p>
                </div>
              </div>

              <Tabs value={entryMethod} onValueChange={(v) => setEntryMethod(v as 'upload' | 'manual')}>
                <TabsList className="grid w-full grid-cols-2 h-12">
                  <TabsTrigger value="upload" className="gap-2 text-sm">
                    <Upload className="h-4 w-4" />
                    <span className="hidden sm:inline">Upload Resume</span>
                    <span className="sm:hidden">Upload</span>
                  </TabsTrigger>
                  <TabsTrigger value="manual" className="gap-2 text-sm">
                    <Edit3 className="h-4 w-4" />
                    <span className="hidden sm:inline">Enter Manually</span>
                    <span className="sm:hidden">Manual</span>
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="upload" className="mt-6 space-y-6">
                  {/* AI Info Banner */}
                  <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-100">
                    <div className="p-2 rounded-lg bg-purple-100">
                      <Sparkles className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-900 mb-1">AI-Powered Resume Parsing</h4>
                      <p className="text-sm text-slate-600">
                        Our AI will extract your skills, experience, and education automatically. 
                        You can review and edit everything in the next step.
                      </p>
                    </div>
                  </div>

                  {/* Upload area */}
                  <DocumentUpload
                    onFilesChange={handleResumeUpload}
                    maxFiles={1}
                    maxSizeInMB={10}
                    acceptedFileTypes={[
                      'application/pdf',
                      'application/msword',
                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ]}
                    documentType="resume"
                    label="Upload Your Resume"
                    description="Drag and drop your resume here, or click to browse"
                  />

                  {/* Parsing status */}
                  {isParsing && (
                    <div className="flex items-center gap-4 p-4 bg-blue-50 rounded-xl border border-blue-100">
                      <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                      <div>
                        <h4 className="font-medium text-blue-900">Analyzing your resume...</h4>
                        <p className="text-sm text-blue-700">This usually takes a few seconds</p>
                      </div>
                    </div>
                  )}

                  {/* Success status */}
                  {parsedData && !isParsing && (
                    <div className="flex items-center gap-4 p-4 bg-green-50 rounded-xl border border-green-200">
                      <CheckCircle2 className="h-6 w-6 text-green-600" />
                      <div>
                        <h4 className="font-medium text-green-900">Resume parsed successfully!</h4>
                        <p className="text-sm text-green-700">Click "Next" to review and edit the extracted information</p>
                      </div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="manual" className="mt-6">
                  <div className="text-center py-12 px-6 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-100 mb-4">
                      <Edit3 className="h-8 w-8 text-slate-500" />
                    </div>
                    <h4 className="font-medium text-slate-900 mb-2">Manual Entry Mode</h4>
                    <p className="text-sm text-slate-600 max-w-sm mx-auto">
                      Prefer not to upload a resume? No problem. Click "Next" to enter your 
                      professional details manually.
                    </p>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}

          {/* Step 3: Edit Professional Information (single edit view, no separate preview) */}
          {currentStep === 3 && (
            <div className="space-y-8">
              {/* Header */}
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-100">
                  <Edit3 className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Professional Information</h3>
                  <p className="text-sm text-slate-500">
                    {parsedData 
                      ? "We've pre-filled fields from your resume. Please review and update as needed."
                      : "Tell us about your professional background and skills."}
                  </p>
                </div>
              </div>

              <Form {...professionalForm}>
                <form className="space-y-8">
                  {/* Section 1: Role & Experience */}
                  <div className="p-6 bg-slate-50 rounded-xl space-y-4">
                    <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                      <User className="h-4 w-4" />
                      Role & Experience
                    </h4>
                    <div className="grid gap-4 md:grid-cols-3">
                      <FormField
                        control={professionalForm.control}
                        name="position"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Desired Position</FormLabel>
                            <FormControl>
                              <Input placeholder="e.g., Software Engineer" className="h-11 bg-white" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={professionalForm.control}
                        name="experience_years"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Years of Experience</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min={0}
                                max={50}
                                placeholder="0"
                                className="h-11 bg-white"
                                {...field}
                                onChange={(e) =>
                                  field.onChange(e.target.value ? parseInt(e.target.value) : undefined)
                                }
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={professionalForm.control}
                        name="expected_salary"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Expected Pay Rate <span className="text-red-500">*</span></FormLabel>
                            <FormControl>
                              <Input
                                placeholder="e.g., $80/hr or $150K/year"
                                className="h-11 bg-white"
                                {...field}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>

                  {/* Section 2: Preferences */}
                  <div className="p-6 bg-blue-50 rounded-xl space-y-6">
                    <h4 className="text-sm font-semibold text-blue-700 uppercase tracking-wide flex items-center gap-2">
                      <Eye className="h-4 w-4" />
                      Job Preferences
                    </h4>
                    
                    <div className="grid gap-6 md:grid-cols-2">
                      {/* Preferred Roles */}
                      <div className="space-y-2">
                        <Label className="text-slate-700">Preferred Job Roles</Label>
                        <TagInput
                          value={preferredRoles}
                          onChange={(roles) => {
                            if (roles.length > 10) {
                              toast.error('Maximum 10 preferred roles allowed');
                              return;
                            }
                            setPreferredRoles(roles);
                          }}
                          placeholder="Add role and press Enter..."
                        />
                        <p className="text-xs text-slate-500">
                          {preferredRoles.length}/10 roles
                        </p>
                      </div>

                      {/* Preferred Locations */}
                      <div className="space-y-2">
                        <Label className="text-slate-700">Preferred Locations</Label>
                        <TagInput
                          value={preferredLocations}
                          onChange={(locations) => {
                            if (locations.length > 10) {
                              toast.error('Maximum 10 locations allowed');
                              return;
                            }
                            setPreferredLocations(locations);
                          }}
                          placeholder="Add location and press Enter..."
                        />
                        <p className="text-xs text-slate-500">
                          {preferredLocations.length}/10 locations
                        </p>
                      </div>
                    </div>

                    {/* AI Role Suggestions */}
                    <div className="pt-4 border-t border-blue-200">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-purple-600" />
                          <span className="text-sm font-medium text-slate-700">AI Role Suggestions</span>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleGenerateRoleSuggestions}
                          disabled={isGeneratingRoles || (!skillTags.length && !workExperience.length && !professionalForm.getValues('position'))}
                          className="bg-white"
                        >
                          {isGeneratingRoles ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Generating...
                            </>
                          ) : (
                            <>
                              <Sparkles className="h-4 w-4 mr-2" />
                              Generate Suggestions
                            </>
                          )}
                        </Button>
                      </div>

                      {suggestedRoles ? (
                        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                          {suggestedRoles.roles.slice(0, 5).map((suggestion, index) => (
                            <div
                              key={index}
                              className="p-3 bg-white rounded-lg border border-slate-200 hover:border-purple-300 transition-colors"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <p className="font-medium text-sm text-slate-900">{suggestion.role}</p>
                                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">{suggestion.reasoning}</p>
                                </div>
                                <Badge
                                  className={`text-xs shrink-0 ${
                                    suggestion.score >= 0.8
                                      ? 'bg-green-100 text-green-700'
                                      : suggestion.score >= 0.6
                                        ? 'bg-yellow-100 text-yellow-700'
                                        : 'bg-slate-100 text-slate-600'
                                  }`}
                                >
                                  {(suggestion.score * 100).toFixed(0)}%
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-500 text-center py-4">
                          Add skills or experience to get AI-powered role recommendations
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Section 3: Skills */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" />
                      Skills & Expertise
                    </h4>
                    <div className="space-y-2">
                      <TagInput
                        value={skillTags}
                        onChange={setSkillTags}
                        placeholder="Add a skill (e.g., React, Python, SQL)..."
                      />
                      <p className="text-xs text-slate-500">
                        Press Enter to add a skill. Click X to remove.
                      </p>
                    </div>
                  </div>

                  {/* Section 4: Work Experience */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Work Experience
                    </h4>
                    <WorkExperienceEditor
                      value={workExperience}
                      onChange={setWorkExperience}
                    />
                  </div>

                  {/* Section 5: Education */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                      <User className="h-4 w-4" />
                      Education
                    </h4>
                    <EducationEditor
                      value={education}
                      onChange={setEducation}
                    />
                  </div>

                  {/* Section 6: Professional Summary */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                      <Edit3 className="h-4 w-4" />
                      Professional Summary
                    </h4>
                    <FormField
                      control={professionalForm.control}
                      name="summary"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Textarea
                              placeholder="Write a brief summary of your professional background, key achievements, and career goals..."
                              rows={4}
                              className="resize-none"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription className="text-xs">
                            Minimum 50 characters. A good summary helps recruiters understand your profile quickly.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </form>
              </Form>
            </div>
          )}

          {/* Step 4: Documents (Dynamic based on tenant requirements) */}
          {currentStep === 4 && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-100">
                  <Paperclip className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Supporting Documents</h3>
                  <p className="text-sm text-slate-500">
                    {documentRequirements.length > 0 
                      ? 'Upload the required documents to complete your application'
                      : 'Upload any additional documents that support your application'}
                  </p>
                </div>
              </div>

              {isLoadingRequirements ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-slate-400 mr-2" />
                  <span className="text-slate-500">Loading requirements...</span>
                </div>
              ) : documentRequirements.length > 0 ? (
                <div className="space-y-6">
                  {/* Required documents */}
                  {documentRequirements.filter(req => req.is_required).length > 0 && (
                    <div className="space-y-4">
                      <h4 className="text-sm font-medium text-slate-700 flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-red-500" />
                        Required Documents
                      </h4>
                      {documentRequirements.filter(req => req.is_required).map((req) => (
                        <div key={req.id} className="p-5 bg-red-50 border border-red-100 rounded-xl">
                          <div className="mb-4">
                            <div className="flex items-center gap-2 mb-1">
                              <h5 className="font-medium text-slate-900">{req.label}</h5>
                              <Badge variant="outline" className="bg-red-100 text-red-700 border-red-200 text-xs">
                                Required
                              </Badge>
                            </div>
                            {req.description && (
                              <p className="text-sm text-slate-600">{req.description}</p>
                            )}
                            <p className="text-xs text-slate-500 mt-1">
                              Formats: {getFileTypeLabels(req.allowed_file_types)} | Max: {req.max_file_size_mb}MB
                            </p>
                          </div>
                          <DocumentUpload
                            onFilesChange={(files) => handleDocumentFileChange(req.document_type, files)}
                            maxFiles={1}
                            maxSizeInMB={req.max_file_size_mb}
                            acceptedFileTypes={getMimeTypesFromExtensions(req.allowed_file_types)}
                            documentType={req.document_type}
                            label={`Upload ${req.label}`}
                            description="Click or drag to upload"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Optional documents */}
                  {documentRequirements.filter(req => !req.is_required).length > 0 && (
                    <div className="space-y-4">
                      <h4 className="text-sm font-medium text-slate-700 flex items-center gap-2">
                        <Paperclip className="h-4 w-4 text-slate-500" />
                        Optional Documents
                      </h4>
                      {documentRequirements.filter(req => !req.is_required).map((req) => (
                        <div key={req.id} className="p-5 bg-slate-50 border border-slate-200 rounded-xl">
                          <div className="mb-4">
                            <div className="flex items-center gap-2 mb-1">
                              <h5 className="font-medium text-slate-900">{req.label}</h5>
                              <Badge variant="outline" className="text-xs">Optional</Badge>
                            </div>
                            {req.description && (
                              <p className="text-sm text-slate-600">{req.description}</p>
                            )}
                            <p className="text-xs text-slate-500 mt-1">
                              Formats: {getFileTypeLabels(req.allowed_file_types)} | Max: {req.max_file_size_mb}MB
                            </p>
                          </div>
                          <DocumentUpload
                            onFilesChange={(files) => handleDocumentFileChange(req.document_type, files)}
                            maxFiles={1}
                            maxSizeInMB={req.max_file_size_mb}
                            acceptedFileTypes={getMimeTypesFromExtensions(req.allowed_file_types)}
                            documentType={req.document_type}
                            label={`Upload ${req.label}`}
                            description="Click or drag to upload"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Additional documents */}
                  <div className="pt-6 border-t">
                    <h4 className="text-sm font-medium text-slate-700 mb-4">Other Documents</h4>
                    <DocumentUpload
                      onFilesChange={setAdditionalFiles}
                      maxFiles={5}
                      maxSizeInMB={10}
                      acceptedFileTypes={[
                        'application/pdf',
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'image/jpeg',
                        'image/png',
                      ]}
                      documentType="other"
                      label="Upload Additional Documents"
                      description="Certifications, portfolio samples, or other relevant files"
                    />
                  </div>
                </div>
              ) : (
                /* No requirements configured */
                <div className="space-y-6">
                  <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
                    <p className="text-sm text-blue-800">
                      <AlertCircle className="inline h-4 w-4 mr-1" />
                      No specific documents are required, but you can upload any supporting materials.
                    </p>
                  </div>
                  <DocumentUpload
                    onFilesChange={setAdditionalFiles}
                    maxFiles={5}
                    maxSizeInMB={10}
                    acceptedFileTypes={[
                      'application/pdf',
                      'application/msword',
                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                      'image/jpeg',
                      'image/png',
                    ]}
                    documentType="other"
                    label="Upload Documents"
                    description="Certifications, portfolio, work authorization, or other relevant documents"
                  />
                </div>
              )}
            </div>
          )}

          {/* Step 5: Final Review & Submit */}
          {currentStep === 5 && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-100">
                  <Eye className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Review Your Application</h3>
                  <p className="text-sm text-slate-500">
                    Please verify all information before submitting
                  </p>
                </div>
              </div>

              {/* Review Cards */}
              <div className="grid gap-4 md:grid-cols-2">
                {/* Personal Info Card */}
                <div className="p-5 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 mb-4">
                    <User className="h-4 w-4 text-slate-600" />
                    <h4 className="font-medium text-slate-700">Personal Information</h4>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Full Name</p>
                      <p className="font-medium text-slate-900">
                        {personalForm.getValues('first_name')} {personalForm.getValues('last_name')}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Email</p>
                      <p className="text-slate-900">{personalForm.getValues('email')}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Phone</p>
                      <p className="text-slate-900">{personalForm.getValues('phone') || '-'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Location</p>
                      <p className="text-slate-900">{personalForm.getValues('location') || '-'}</p>
                    </div>
                  </div>
                </div>

                {/* Professional Info Card */}
                <div className="p-5 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 mb-4">
                    <FileText className="h-4 w-4 text-slate-600" />
                    <h4 className="font-medium text-slate-700">Professional Details</h4>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Desired Position</p>
                      <p className="font-medium text-slate-900">
                        {professionalForm.getValues('position') || '-'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Experience</p>
                      <p className="text-slate-900">
                        {professionalForm.getValues('experience_years') || 0} years
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Expected Pay Rate</p>
                      <p className="text-slate-900">
                        {professionalForm.getValues('expected_salary') || '-'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Skills */}
              {skillTags.length > 0 && (
                <div className="p-5 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 className="h-4 w-4 text-slate-600" />
                    <h4 className="font-medium text-slate-700">Skills ({skillTags.length})</h4>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {skillTags.map((skill, idx) => (
                      <Badge key={idx} variant="secondary" className="bg-white">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Preferences */}
              {(preferredRoles.length > 0 || preferredLocations.length > 0) && (
                <div className="grid gap-4 md:grid-cols-2">
                  {preferredRoles.length > 0 && (
                    <div className="p-5 bg-blue-50 rounded-xl">
                      <h4 className="font-medium text-slate-700 mb-3">Preferred Roles</h4>
                      <div className="flex flex-wrap gap-2">
                        {preferredRoles.map((role, idx) => (
                          <Badge key={idx} className="bg-blue-100 text-blue-700">{role}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {preferredLocations.length > 0 && (
                    <div className="p-5 bg-green-50 rounded-xl">
                      <h4 className="font-medium text-slate-700 mb-3">Preferred Locations</h4>
                      <div className="flex flex-wrap gap-2">
                        {preferredLocations.map((loc, idx) => (
                          <Badge key={idx} className="bg-green-100 text-green-700">{loc}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Work Experience Summary */}
              {workExperience.length > 0 && (
                <div className="p-5 bg-slate-50 rounded-xl">
                  <h4 className="font-medium text-slate-700 mb-3">Work Experience ({workExperience.length})</h4>
                  <div className="space-y-2">
                    {workExperience.slice(0, 3).map((exp, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="font-medium text-slate-900">{exp.title}</span>
                        <span className="text-slate-600">{exp.company}</span>
                      </div>
                    ))}
                    {workExperience.length > 3 && (
                      <p className="text-xs text-slate-500">+{workExperience.length - 3} more</p>
                    )}
                  </div>
                </div>
              )}

              {/* Education Summary */}
              {education.length > 0 && (
                <div className="p-5 bg-slate-50 rounded-xl">
                  <h4 className="font-medium text-slate-700 mb-3">Education ({education.length})</h4>
                  <div className="space-y-2">
                    {education.slice(0, 2).map((edu, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="font-medium text-slate-900">{edu.degree}</span>
                        <span className="text-slate-600">{edu.institution}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Documents Summary */}
              <div className="p-5 bg-slate-50 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <Paperclip className="h-4 w-4 text-slate-600" />
                  <h4 className="font-medium text-slate-700">Uploaded Documents</h4>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    {resumeFiles.length > 0 ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-slate-400" />
                    )}
                    <span className={resumeFiles.length > 0 ? 'text-slate-900' : 'text-slate-500'}>
                      Resume: {resumeFiles.length > 0 ? resumeFiles[0].file.name : (entryMethod === 'manual' ? 'Manual entry' : 'Not uploaded')}
                    </span>
                  </div>
                  {documentRequirements.map((req) => {
                    const files = documentFiles[req.document_type] || [];
                    return (
                      <div key={req.id} className="flex items-center gap-2">
                        {files.length > 0 ? (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        ) : req.is_required ? (
                          <AlertTriangle className="h-4 w-4 text-amber-500" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-slate-400" />
                        )}
                        <span className={files.length > 0 ? 'text-slate-900' : 'text-slate-500'}>
                          {req.label}: {files.length > 0 ? files[0].file.name : 'Not uploaded'}
                        </span>
                      </div>
                    );
                  })}
                  {additionalFiles.length > 0 && (
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-slate-900">
                        {additionalFiles.length} additional document(s)
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* AI Badge */}
              {parsedData && (
                <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-100">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                  <p className="text-sm text-slate-700">
                    Your application includes AI-extracted information from your resume
                  </p>
                </div>
              )}
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between border-t p-6 bg-slate-50">
          <Button
            variant="ghost"
            onClick={handlePrevStep}
            disabled={currentStep === 1 || isSubmitting}
            className="gap-2"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>

          {currentStep < steps.length ? (
            <Button 
              onClick={handleNextStep} 
              disabled={isSubmitting || (currentStep === 2 && isParsing)}
              className="gap-2 bg-slate-900 hover:bg-slate-800"
            >
              {currentStep === 2 && isParsing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Parsing...
                </>
              ) : (
                <>
                  Next
                  <ChevronRight className="h-4 w-4" />
                </>
              )}
            </Button>
          ) : (
            <Button 
              onClick={() => setShowConfirmDialog(true)} 
              disabled={isSubmitting}
              className="gap-2 bg-green-600 hover:bg-green-700"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Submit Application
                </>
              )}
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>

      {/* Confirmation Dialog - Improved styling */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-full bg-amber-100">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
              </div>
              <AlertDialogTitle className="text-xl">Ready to Submit?</AlertDialogTitle>
            </div>
            <AlertDialogDescription asChild>
              <div className="space-y-4">
                <p className="text-slate-600">
                  Please confirm you're ready to submit your application.
                </p>
                <div className="bg-slate-50 rounded-lg p-4 space-y-2">
                  <div className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-slate-500 mt-0.5 shrink-0" />
                    <span>Your application cannot be modified after submission</span>
                  </div>
                  <div className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-slate-500 mt-0.5 shrink-0" />
                    <span>Our team will review and respond within 2-3 business days</span>
                  </div>
                  <div className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-slate-500 mt-0.5 shrink-0" />
                    <span>You'll receive a confirmation email at {personalForm.getValues('email')}</span>
                  </div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="gap-2">
            <AlertDialogCancel disabled={isSubmitting} className="flex-1">
              Go Back
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="flex-1 bg-green-600 hover:bg-green-700"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Submit Now
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
