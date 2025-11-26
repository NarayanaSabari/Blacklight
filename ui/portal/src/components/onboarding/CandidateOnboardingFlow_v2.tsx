/**
 * CandidateOnboardingFlow Component (v2 with AI Resume Parsing)
 * Multi-step wizard for candidate self-onboarding with AI resume parsing
 * Steps: 
 * 1) Personal Info
 * 2) Resume Upload + AI Parsing (with manual entry option)
 * 3) Review & Edit Parsed Data
 * 4) Additional Documents
 * 5) Final Review & Submit
 */

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
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
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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
} from 'lucide-react';
import { DocumentUpload, type UploadedFile } from '@/components/documents/DocumentUpload';
import { useSubmitOnboarding, useUploadOnboardingDocument } from '@/hooks/useOnboarding';
import { onboardingApi } from '@/lib/api/invitationApi';
import type { InvitationWithRelations } from '@/types';
import { toast } from 'sonner';
import { TagInput } from '@/components/ui/tag-input';
import { WorkExperienceEditor } from '@/components/candidates/WorkExperienceEditor';
import { EducationEditor } from '@/components/candidates/EducationEditor';
import { Label } from '@/components/ui/label';

const personalInfoSchema = z.object({
  first_name: z.string().min(2, 'First name must be at least 2 characters'),
  last_name: z.string().min(2, 'Last name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  phone: z.string().optional(),
  location: z.string().optional(),
  linkedin_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  github_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  portfolio_url: z.string().url('Invalid URL').optional().or(z.literal('')),
});

const professionalInfoSchema = z.object({
  position: z.string().optional(),
  experience_years: z.number().min(0).max(50).optional(),
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
    }
  }, [parsedData, originalParsedData, currentStep, professionalForm, personalForm]);

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

    setCurrentStep((prev) => Math.min(prev + 1, steps.length));
  };

  const handlePrevStep = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
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

      // Upload additional documents
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

      await submitMutation.mutateAsync({
        token,
        data: {
          ...personalData,
          position: professionalData.position,
          experience_years: professionalData.experience_years,
          skills,
          education: professionalData.education,
          work_experience: professionalData.work_experience,
          summary: professionalData.summary,
          parsed_resume_data: Object.keys(mergedParsed).length > 0 ? mergedParsed : undefined,
        },
      });

      onSuccess();
    } catch (error) {
      console.error('Onboarding submission failed:', error);
    }
  };

  const isSubmitting = submitMutation.isPending || uploadMutation.isPending;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Progress Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Complete Your Onboarding</CardTitle>
              <CardDescription>
                Step {currentStep} of {steps.length}
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-base">
              {Math.round(progress)}%
            </Badge>
          </div>
          <Progress value={progress} className="mt-4" />
        </CardHeader>
        <CardContent>
          <div className="flex justify-between">
            {steps.map((step) => {
              const Icon = step.icon;
              const isActive = step.number === currentStep;
              const isCompleted = step.number < currentStep;

              return (
                <div
                  key={step.number}
                  className={`flex flex-col items-center gap-2 ${
                    isActive ? 'text-primary' : isCompleted ? 'text-green-600' : 'text-muted-foreground'
                  }`}
                >
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                      isActive
                        ? 'border-primary bg-primary/10'
                        : isCompleted
                        ? 'border-green-600 bg-green-50'
                        : 'border-muted'
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  <span className="text-xs font-medium">{step.title}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Step Content */}
      <Card>
        <CardContent className="pt-6">
          {/* Step 1: Personal Info */}
          {currentStep === 1 && (
            <Form {...personalForm}>
              <form className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-4">Personal Information</h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    <FormField
                      control={personalForm.control}
                      name="first_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>First Name *</FormLabel>
                          <FormControl>
                            <Input placeholder="John" {...field} />
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
                          <FormLabel>Last Name *</FormLabel>
                          <FormControl>
                            <Input placeholder="Doe" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>

                <Separator />

                <div className="grid gap-4 md:grid-cols-2">
                  <FormField
                    control={personalForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Email *</FormLabel>
                        <FormControl>
                          <Input type="email" placeholder="john@example.com" {...field} disabled />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={personalForm.control}
                    name="phone"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Phone</FormLabel>
                        <FormControl>
                          <Input placeholder="+1 (555) 123-4567" {...field} />
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
                        <Input placeholder="San Francisco, CA" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Separator />

                <div>
                  <h4 className="text-sm font-medium mb-4">Online Profiles (Optional)</h4>
                  <div className="space-y-4">
                    <FormField
                      control={personalForm.control}
                      name="linkedin_url"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>LinkedIn</FormLabel>
                          <FormControl>
                            <Input placeholder="https://linkedin.com/in/johndoe" {...field} />
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
                          <FormLabel>GitHub</FormLabel>
                          <FormControl>
                            <Input placeholder="https://github.com/johndoe" {...field} />
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
                          <FormLabel>Portfolio</FormLabel>
                          <FormControl>
                            <Input placeholder="https://johndoe.com" {...field} />
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
              <div>
                <h3 className="text-lg font-semibold mb-2">Resume & Professional Information</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Upload your resume for AI-powered parsing, or enter details manually.
                </p>
              </div>

              <Tabs value={entryMethod} onValueChange={(v) => setEntryMethod(v as 'upload' | 'manual')}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="upload" className="flex items-center gap-2">
                    <Upload className="h-4 w-4" />
                    Upload Resume (AI Parsing)
                  </TabsTrigger>
                  <TabsTrigger value="manual" className="flex items-center gap-2">
                    <Edit3 className="h-4 w-4" />
                    Enter Manually
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="upload" className="space-y-4 mt-6">
                  <Alert>
                    <Sparkles className="h-4 w-4" />
                    <AlertTitle>AI-Powered Resume Parsing</AlertTitle>
                    <AlertDescription>
                      Upload your resume and our AI will automatically extract your information. You'll be able to review and edit everything in the next step.
                    </AlertDescription>
                  </Alert>

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
                    label="Upload Resume"
                    description="Drag and drop your resume here, or click to browse (PDF or DOCX)"
                  />

                  {isParsing && (
                    <Alert>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <AlertTitle>Parsing your resume...</AlertTitle>
                      <AlertDescription>
                        Our AI is analyzing your resume. This usually takes a few seconds.
                      </AlertDescription>
                    </Alert>
                  )}

                  {parsedData && (
                    <Alert className="border-green-600">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <AlertTitle className="text-green-600">Resume Parsed Successfully!</AlertTitle>
                      <AlertDescription>
                        We've extracted information from your resume. Click "Next" to review and edit the details.
                      </AlertDescription>
                    </Alert>
                  )}
                </TabsContent>

                <TabsContent value="manual" className="space-y-4 mt-6">
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Manual Entry</AlertTitle>
                    <AlertDescription>
                      If you prefer not to upload a resume, you can enter your professional details manually in the next step.
                    </AlertDescription>
                  </Alert>

                  <div className="p-6 border rounded-lg bg-muted/30">
                    <p className="text-sm text-center text-muted-foreground">
                      Click "Next" to enter your professional information manually.
                    </p>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}

          {/* Step 3: Edit Professional Information (single edit view, no separate preview) */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">
                  Professional Information
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  We’ve pre-filled these fields where possible using your resume. Please review and
                  update anything that’s missing or inaccurate.
                </p>
              </div>

              <Form {...professionalForm}>
                <form className="space-y-8">
                  {/* Position & Experience – mirrors top of professional section on candidate detail page */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-900">Role & Experience</h4>
                    <div className="grid gap-4 md:grid-cols-2">
                      <FormField
                        control={professionalForm.control}
                        name="position"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Desired Position</FormLabel>
                            <FormControl>
                              <Input placeholder="Software Engineer" {...field} />
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
                            <FormLabel>Total Experience (years)</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min={0}
                                max={50}
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
                    </div>
                  </div>

                  <Separator />

                  {/* Skills – structured chips, like candidate detail page */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-900">Skills</h4>
                    <div className="space-y-2">
                      <Label>Skills</Label>
                      <TagInput
                        value={skillTags}
                        onChange={setSkillTags}
                        placeholder="Add a skill (e.g., React, Python)..."
                      />
                      <p className="text-xs text-slate-500">
                        Press Enter to add a skill. Click X to remove.
                      </p>
                    </div>
                  </div>

                  <Separator />

                  {/* Work Experience – structured editor like candidate detail page */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-900">Work Experience</h4>
                    <WorkExperienceEditor
                      value={workExperience}
                      onChange={setWorkExperience}
                    />
                  </div>

                  <Separator />

                  {/* Education – structured editor like candidate detail page */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-900">Education</h4>
                    <EducationEditor
                      value={education}
                      onChange={setEducation}
                    />
                  </div>

                  <Separator />

                  {/* Professional Summary – aligns with Professional Summary card */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-slate-900">Professional Summary</h4>
                    <FormField
                      control={professionalForm.control}
                      name="summary"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Summary</FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="Brief summary of your professional background, key achievements, and career goals..."
                              rows={4}
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>At least 50 characters</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </form>
              </Form>
            </div>
          )}

          {/* Step 4: Additional Documents */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Additional Documents (Optional)</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Upload any additional documents such as ID proof, work authorization, certifications, or portfolio samples.
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
                label="Upload Additional Documents"
                description="Optional: Add certifications, portfolio, work authorization, or other relevant documents"
              />
            </div>
          )}

          {/* Step 5: Final Review & Submit */}
          {currentStep === 5 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Final Review</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Please review all information before submitting your application.
                </p>
              </div>

              <div className="space-y-4">
                <ReviewSection title="Personal Information">
                  <ReviewItem label="Name" value={`${personalForm.getValues('first_name')} ${personalForm.getValues('last_name')}`} />
                  <ReviewItem label="Email" value={personalForm.getValues('email')} />
                  <ReviewItem label="Phone" value={personalForm.getValues('phone') || 'Not provided'} />
                  <ReviewItem label="Location" value={personalForm.getValues('location') || 'Not provided'} />
                  {personalForm.getValues('linkedin_url') && (
                    <ReviewItem label="LinkedIn" value={personalForm.getValues('linkedin_url')!} />
                  )}
                </ReviewSection>

                <Separator />

                <ReviewSection title="Professional Information">
                  <ReviewItem label="Position" value={professionalForm.getValues('position') || 'Not provided'} />
                  <ReviewItem label="Experience" value={`${professionalForm.getValues('experience_years') || 0} years`} />
                  <ReviewItem label="Skills" value={professionalForm.getValues('skills') || 'Not provided'} />
                </ReviewSection>

                {professionalForm.getValues('work_experience') && (
                  <>
                    <Separator />
                    <ReviewSection title="Work Experience">
                      <div className="text-sm whitespace-pre-line">{professionalForm.getValues('work_experience')}</div>
                    </ReviewSection>
                  </>
                )}

                {professionalForm.getValues('education') && (
                  <>
                    <Separator />
                    <ReviewSection title="Education">
                      <div className="text-sm whitespace-pre-line">{professionalForm.getValues('education')}</div>
                    </ReviewSection>
                  </>
                )}

                <Separator />

                <ReviewSection title="Documents">
                  <div className="space-y-2">
                    <div>
                      <span className="text-sm font-medium">Resume:</span>
                      <span className="text-sm text-muted-foreground ml-2">
                        {resumeFiles.length > 0 ? resumeFiles[0].file.name : entryMethod === 'manual' ? 'Entered manually' : 'Not uploaded'}
                      </span>
                    </div>
                    <div>
                      <span className="text-sm font-medium">Additional Documents:</span>
                      <span className="text-sm text-muted-foreground ml-2">
                        {additionalFiles.length > 0 ? `${additionalFiles.length} file(s)` : 'None'}
                      </span>
                    </div>
                  </div>
                </ReviewSection>

                {parsedData && (
                  <Alert className="border-blue-600 bg-blue-50/50">
                    <Sparkles className="h-4 w-4 text-blue-600" />
                    <AlertTitle className="text-blue-600">AI-Assisted Application</AlertTitle>
                    <AlertDescription>
                      Your application includes information extracted using AI resume parsing technology.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between border-t pt-6">
          <Button
            variant="outline"
            onClick={handlePrevStep}
            disabled={currentStep === 1 || isSubmitting}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Previous
          </Button>

          {currentStep < steps.length ? (
            <Button onClick={handleNextStep} disabled={isSubmitting || (currentStep === 2 && isParsing)}>
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Submit Application
                </>
              )}
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}

function ReviewSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-3">{title}</h4>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function ReviewItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
