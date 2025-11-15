/**
 * CandidateOnboardingFlow Component
 * Multi-step wizard for candidate self-onboarding with AI resume parsing
 * Steps: 1) Personal Info, 2) Resume Upload + AI Parsing, 3) Review Parsed Data, 4) Additional Documents, 5) Final Review & Submit
 */

import { useState } from 'react';
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
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { DocumentUpload, type UploadedFile } from '@/components/documents/DocumentUpload';
import { useSubmitOnboarding, useUploadOnboardingDocument } from '@/hooks/useOnboarding';
import type { InvitationWithRelations } from '@/types';

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
  summary: z.string().min(50, 'Summary must be at least 50 characters').optional().or(z.literal('')),
});

type PersonalInfoValues = z.infer<typeof personalInfoSchema>;
type ProfessionalInfoValues = z.infer<typeof professionalInfoSchema>;

interface CandidateOnboardingFlowProps {
  token: string;
  invitation: InvitationWithRelations;
  onSuccess: () => void;
}

export function CandidateOnboardingFlow({
  token,
  invitation,
  onSuccess,
}: CandidateOnboardingFlowProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [resumeFiles, setResumeFiles] = useState<UploadedFile[]>([]);
  const [additionalFiles, setAdditionalFiles] = useState<UploadedFile[]>([]);

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
      summary: '',
    },
  });

  const steps = [
    { number: 1, title: 'Personal Info', icon: User },
    { number: 2, title: 'Resume', icon: FileText },
    { number: 3, title: 'Documents', icon: Paperclip },
    { number: 4, title: 'Review', icon: Eye },
  ];

  const progress = (currentStep / steps.length) * 100;

  const handleNextStep = async () => {
    if (currentStep === 1) {
      const isValid = await personalForm.trigger();
      if (!isValid) return;
    }

    if (currentStep === 2 && resumeFiles.length === 0) {
      // Resume is required
      alert('Please upload your resume');
      return;
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
      // Upload resume first
      for (const file of resumeFiles) {
        if (file.status === 'pending') {
          await uploadMutation.mutateAsync({
            token,
            file: file.file,
            documentType: 'resume',
          });
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

      // Submit onboarding data
      const skills = professionalData.skills
        ? professionalData.skills.split(',').map((s) => s.trim())
        : undefined;

      await submitMutation.mutateAsync({
        token,
        data: {
          ...personalData,
          ...professionalData,
          skills,
        },
      });

      onSuccess();
    } catch (error) {
      // Errors handled by mutations
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

          {/* Step 2: Resume Upload */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Upload Your Resume</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Please upload your latest resume in PDF or DOCX format.
                </p>
              </div>
              <DocumentUpload
                onFilesChange={setResumeFiles}
                maxFiles={1}
                maxSizeInMB={10}
                acceptedFileTypes={[
                  'application/pdf',
                  'application/msword',
                  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                ]}
                documentType="resume"
                label="Upload Resume"
                description="Drag and drop your resume here, or click to browse"
              />

              <Separator />

              <Form {...professionalForm}>
                <form className="space-y-4">
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
                        <FormLabel>Years of Experience</FormLabel>
                        <FormControl>
                          <Input 
                            type="number" 
                            min={0} 
                            max={50} 
                            {...field}
                            onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={professionalForm.control}
                    name="skills"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Skills</FormLabel>
                        <FormControl>
                          <Input placeholder="JavaScript, React, Node.js, Python" {...field} />
                        </FormControl>
                        <FormDescription>Separate multiple skills with commas</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </form>
              </Form>
            </div>
          )}

          {/* Step 3: Additional Documents */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Additional Documents</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Upload any additional documents such as certifications, portfolio samples, or
                  references (optional).
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
                description="Optional: Add certifications, portfolio, or other relevant documents"
              />

              <Separator />

              <Form {...professionalForm}>
                <form className="space-y-4">
                  <FormField
                    control={professionalForm.control}
                    name="education"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Education</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Bachelor's in Computer Science, University of XYZ, 2020"
                            rows={2}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={professionalForm.control}
                    name="summary"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Professional Summary</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Brief summary of your professional background and career goals..."
                            rows={4}
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>At least 50 characters</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </form>
              </Form>
            </div>
          )}

          {/* Step 4: Review & Submit */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Review Your Information</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Please review all information before submitting.
                </p>
              </div>

              <div className="space-y-4">
                <ReviewSection title="Personal Information">
                  <ReviewItem label="Name" value={`${personalForm.getValues('first_name')} ${personalForm.getValues('last_name')}`} />
                  <ReviewItem label="Email" value={personalForm.getValues('email')} />
                  <ReviewItem label="Phone" value={personalForm.getValues('phone') || 'Not provided'} />
                  <ReviewItem label="Location" value={personalForm.getValues('location') || 'Not provided'} />
                </ReviewSection>

                <Separator />

                <ReviewSection title="Professional Information">
                  <ReviewItem label="Position" value={professionalForm.getValues('position') || 'Not provided'} />
                  <ReviewItem label="Experience" value={`${professionalForm.getValues('experience_years') || 0} years`} />
                  <ReviewItem label="Skills" value={professionalForm.getValues('skills') || 'Not provided'} />
                  <ReviewItem label="Education" value={professionalForm.getValues('education') || 'Not provided'} />
                </ReviewSection>

                <Separator />

                <ReviewSection title="Documents">
                  <div className="space-y-2">
                    <div>
                      <span className="text-sm font-medium">Resume:</span>
                      <span className="text-sm text-muted-foreground ml-2">
                        {resumeFiles.length > 0 ? resumeFiles[0].file.name : 'Not uploaded'}
                      </span>
                    </div>
                    <div>
                      <span className="text-sm font-medium">Additional Documents:</span>
                      <span className="text-sm text-muted-foreground ml-2">
                        {additionalFiles.length} file(s)
                      </span>
                    </div>
                  </div>
                </ReviewSection>
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
            <Button onClick={handleNextStep} disabled={isSubmitting}>
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
