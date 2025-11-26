/**
 * Candidate Detail Page - View Mode
 * 
 * Enhanced universal candidate profile view with:
 * - Polished neobrutalist design
 * - Improved visual hierarchy
 * - Complete candidate information display
 * - Resume management & document viewer
 * - Job matching preview
 * - Team assignment tracking
 */

import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Download,
  FileText,
  Briefcase,
  GraduationCap,
  Award,
  Languages,
  MapPin,
  Phone,
  Mail,
  Linkedin,
  Globe,
  Calendar,
  DollarSign,
  Clock,
  RefreshCw,
  Trash2,
  Loader2,
  AlertCircle,
  Pencil,
  UserPlus,
  Users,
  Target,
  Sparkles,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Star,
} from 'lucide-react';
import { toast } from 'sonner';

import { candidateApi } from '@/lib/candidateApi';
import { documentApi } from '@/lib/documentApi';
import { candidateAssignmentApi } from '@/lib/candidateAssignmentApi';
import { jobMatchApi } from '@/lib/jobMatchApi';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { CandidateAssignmentDialog } from '@/components/CandidateAssignmentDialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
import {
  DocumentList,
  DocumentViewer,
  DocumentVerificationModal,
} from '@/components/documents';
import { TagInput } from '@/components/ui/tag-input';
import { WorkExperienceEditor } from '@/components/candidates/WorkExperienceEditor';
import { EducationEditor } from '@/components/candidates/EducationEditor';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { candidateUpdateSchema, type CandidateUpdateInput } from '@/schemas/candidateSchema';
import type { Document, DocumentListItem, Candidate as CandidateType } from '@/types';

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  processing: { color: 'bg-blue-500 text-white', label: 'Processing' },
  pending_review: { color: 'bg-yellow-500 text-white', label: 'Pending Review' },
  new: { color: 'bg-green-500 text-white', label: 'New' },
  screening: { color: 'bg-purple-500 text-white', label: 'Screening' },
  interviewed: { color: 'bg-indigo-500 text-white', label: 'Interviewed' },
  offered: { color: 'bg-orange-500 text-white', label: 'Offered' },
  hired: { color: 'bg-green-600 text-white', label: 'Hired' },
  rejected: { color: 'bg-red-500 text-white', label: 'Rejected' },
  withdrawn: { color: 'bg-gray-500 text-white', label: 'Withdrawn' },
  onboarded: { color: 'bg-teal-500 text-white', label: 'Onboarded' },
  ready_for_assignment: { color: 'bg-cyan-500 text-white', label: 'Ready' },
};

export function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  // Review mode detection
  const searchParams = new URLSearchParams(location.search);
  const isReviewMode = searchParams.get('mode') === 'review';

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showDocumentViewer, setShowDocumentViewer] = useState(false);
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [showAssignmentDialog, setShowAssignmentDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  // We don't currently persist the reject reason, but keep setter for future use
  const [, setRejectReason] = useState('');

  // Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const [formData, setFormData] = useState<CandidateUpdateInput | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Fetch candidate data
  const { data: candidate, isLoading, error } = useQuery({
    queryKey: ['candidate', id],
    queryFn: () => candidateApi.getCandidate(Number(id)),
    enabled: !!id,
  });

  // Fetch candidate documents
  const { data: documentsResponse, isLoading: documentsLoading } = useQuery({
    queryKey: ['documents', 'candidate', id],
    queryFn: () => documentApi.listDocuments({ candidate_id: Number(id) }),
    enabled: !!id,
  });

  // Fetch candidate assignments
  const { data: assignmentsData } = useQuery({
    queryKey: ['candidate-assignments', id],
    queryFn: () => candidateAssignmentApi.getCandidateAssignments(Number(id), false),
    enabled: !!id,
    staleTime: 0,
  });

  // Get current assignment
  const currentAssignment = assignmentsData?.assignments?.find(a => a.status === 'ACTIVE');

  // Fetch top job matches
  const { data: matchesData } = useQuery({
    queryKey: ['candidateMatches', id],
    queryFn: () => jobMatchApi.getCandidateMatches(Number(id), { per_page: 3, sort_by: 'match_score', sort_order: 'desc' }),
    enabled: !!id,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => candidateApi.deleteCandidate(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      toast.success('Candidate deleted successfully');
      navigate('/candidates');
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete candidate: ${error.message}`);
    },
  });

  // Reparse mutation
  const reparseMutation = useMutation({
    mutationFn: () => candidateApi.reparseResume(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidate', id] });
      toast.success('Resume re-parsed successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to re-parse resume: ${error.message}`);
    },
  });

  // Approve mutation (for review mode)
  const approveMutation = useMutation({
    mutationFn: () => candidateApi.approveCandidate(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidate', id] });
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      toast.success('Candidate approved successfully!');
    },
    onError: (error: Error) => {
      toast.error(`Failed to approve: ${error.message}`);
    },
  });

  // Reject mutation (for review mode)
  const rejectMutation = useMutation({
    mutationFn: () => candidateApi.deleteCandidate(Number(id)),
    onSuccess: () => {
      toast.success('Candidate rejected');
      navigate('/candidate-management?tab=onboarding');
    },
    onError: (error: Error) => {
      toast.error(`Failed to reject: ${error.message}`);
    },
  });

  // Role Preferences State
  const [preferredRoles, setPreferredRoles] = useState<string[]>([]);
  const [isGeneratingRoles, setIsGeneratingRoles] = useState(false);

  // Initialize preferred roles from candidate data
  useEffect(() => {
    if (candidate?.preferred_roles) {
      setPreferredRoles(candidate.preferred_roles);
    }
  }, [candidate?.preferred_roles]);

  // Update Preferred Roles Mutation
  const updatePreferredRolesMutation = useMutation({
    mutationFn: (roles: string[]) =>
      candidateApi.updateCandidate(Number(id), { preferred_roles: roles } as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidate', id] });
      toast.success('Preferred roles updated');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update preferred roles: ${error.message}`);
    },
  });

  // Generate AI Role Suggestions Mutation
  const generateRoleSuggestionsMutation = useMutation({
    mutationFn: async () => {
      setIsGeneratingRoles(true);
      const response = await candidateApi.generateRoleSuggestions(Number(id));
      return response;
    },
    onSuccess: (data) => {
      setIsGeneratingRoles(false);

      // Manually update cache to show results immediately
      queryClient.setQueryData(['candidate', id], (oldData: CandidateType | undefined) => {
        if (!oldData) return oldData;
        return {
          ...oldData,
          suggested_roles: data.suggested_roles
        };
      });

      queryClient.invalidateQueries({ queryKey: ['candidate', id] });
      toast.success('AI role suggestions generated!');
    },
    onError: (error: Error) => {
      setIsGeneratingRoles(false);
      toast.error(`Failed to generate suggestions: ${error.message}`);
    },
  });

  // Handle preferred roles update
  const handleUpdatePreferredRoles = (roles: string[]) => {
    if (roles.length > 10) {
      toast.error('Maximum 10 preferred roles allowed');
      return;
    }
    setPreferredRoles(roles);
    updatePreferredRolesMutation.mutate(roles);
  };


  const handleDelete = () => {
    deleteMutation.mutate();
  };

  const handleDownloadResume = () => {
    if (candidate?.resume_file_url) {
      window.open(candidate.resume_file_url, '_blank');
      toast.success('Resume download started');
    } else {
      toast.error('No resume file available');
    }
  };

  const handleReparse = () => {
    reparseMutation.mutate();
  };

  // Document handlers
  const handleViewDocument = (document: DocumentListItem) => {
    documentApi.getDocument(document.id).then((fullDoc) => {
      setSelectedDocument(fullDoc);
      setShowDocumentViewer(true);
    });
  };

  const handleDownloadDocument = async (document: DocumentListItem) => {
    try {
      const blob = await documentApi.downloadDocument(document.id);
      const url = window.URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = document.file_name;
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('Document downloaded successfully');
    } catch {
      toast.error('Failed to download document');
    }
  };

  const handleVerifyDocument = (document: DocumentListItem) => {
    documentApi.getDocument(document.id).then((fullDoc) => {
      setSelectedDocument(fullDoc);
      setShowVerificationModal(true);
    });
  };

  const handleDeleteDocument = async (document: DocumentListItem) => {
    if (confirm(`Are you sure you want to delete ${document.file_name}?`)) {
      try {
        await documentApi.deleteDocument(document.id);
        queryClient.invalidateQueries({ queryKey: ['documents', 'candidate', id] });
        toast.success('Document deleted successfully');
      } catch {
        toast.error('Failed to delete document');
      }
    }
  };

  const handleDocumentVerified = () => {
    queryClient.invalidateQueries({ queryKey: ['documents', 'candidate', id] });
    setShowVerificationModal(false);
    setSelectedDocument(null);
  };

  // Edit mode handlers
  const enterEditMode = () => {
    if (!candidate) return;

    // Initialize form data from candidate
    setFormData({
      first_name: candidate.first_name,
      last_name: candidate.last_name,
      email: candidate.email || '',
      phone: candidate.phone || '',
      full_name: candidate.full_name || '',
      location: candidate.location || '',
      linkedin_url: candidate.linkedin_url || '',
      portfolio_url: candidate.portfolio_url || '',
      current_title: candidate.current_title || '',
      total_experience_years: candidate.total_experience_years,
      notice_period: candidate.notice_period || '',
      expected_salary: candidate.expected_salary || '',
      professional_summary: candidate.professional_summary || '',
      preferred_locations: candidate.preferred_locations || [],
      skills: candidate.skills || [],
      certifications: candidate.certifications || [],
      languages: candidate.languages || [],
      education: candidate.education || [],
      work_experience: candidate.work_experience || [],
      status: candidate.status,
      source: candidate.source,
    });
    setIsEditMode(true);
    setHasUnsavedChanges(false);
    setValidationErrors({});
  };

  const exitEditMode = () => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Are you sure you want to cancel?')) {
        return;
      }
    }
    setIsEditMode(false);
    setFormData(null);
    setHasUnsavedChanges(false);
    setValidationErrors({});
  };

  const updateField = (field: keyof CandidateUpdateInput, value: any) => {
    if (!formData) return;

    setFormData({ ...formData, [field]: value });
    setHasUnsavedChanges(true);

    // Clear validation error for this field
    if (validationErrors[field]) {
      const newErrors = { ...validationErrors };
      delete newErrors[field];
      setValidationErrors(newErrors);
    }
  };

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: CandidateUpdateInput) =>
      candidateApi.updateCandidate(Number(id), data as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidate', id] });
      toast.success('Candidate updated successfully');
      setIsEditMode(false);
      setFormData(null);
      setHasUnsavedChanges(false);
      setValidationErrors({});
    },
    onError: (error: Error) => {
      toast.error(`Failed to update candidate: ${error.message}`);
    },
  });

  const handleSave = async () => {
    if (!formData) return;

    // Validate with Zod
    const result = candidateUpdateSchema.safeParse(formData);

    if (!result.success) {
      const errors: Record<string, string> = {};

      // Map Zod issues to a simple field -> message map
      result.error.issues.forEach((issue) => {
        if (issue.path[0]) {
          errors[issue.path[0].toString()] = issue.message;
        }
      });

      setValidationErrors(errors);
      toast.error('Please fix validation errors before saving');
      return;
    }

    // Save
    updateMutation.mutate(formData);
  };

  // Unsaved changes warning
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // Restrict review mode access to candidates with pending_review status
  useEffect(() => {
    if (isReviewMode && candidate && candidate.status !== 'pending_review') {
      // Redirect to normal candidate detail page if not in review status
      toast.error('Review mode is only available for candidates pending review');
      navigate(`/candidates/${id}`, { replace: true });
    }
  }, [isReviewMode, candidate, id, navigate]);


  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Error state
  if (error || !candidate) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error instanceof Error ? error.message : 'Candidate not found'}
          </AlertDescription>
        </Alert>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => navigate('/candidates')}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Candidates
        </Button>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[candidate.status] || STATUS_CONFIG.new;

  return (
    <div className="space-y-6">
      {/* Review Actions Header (only shown in review mode) */}
      {isReviewMode && (
        <div className="bg-amber-50 border-2 border-amber-500 rounded-lg p-4 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-500 text-white flex items-center justify-center border-2 border-black">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Review Candidate</h3>
                <p className="text-sm text-slate-600 mt-0.5">
                  Approve this candidate, reject them, or edit their profile before approving
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                onClick={() => navigate('/candidate-management?tab=onboarding')}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to List
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                onClick={() => setShowRejectDialog(true)}
                disabled={rejectMutation.isPending}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                onClick={() => isEditMode ? exitEditMode() : enterEditMode()}
              >
                <Pencil className="h-4 w-4 mr-2" />
                {isEditMode ? 'Cancel Edit' : 'Edit'}
              </Button>
              <Button
                size="sm"
                className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                {approveMutation.isPending ? 'Approving...' : 'Approve'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Header Section with Gradient Background */}
      <div className="bg-gradient-to-r from-primary/10 via-secondary/10 to-accent/10 rounded-lg border-2 border-black p-6 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          {/* Left: Name & Title */}
          <div className="flex-1 min-w-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/candidates')}
              className="mb-3 -ml-2"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Candidates
            </Button>

            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                {(candidate.full_name || candidate.first_name).charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-1">
                  {candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
                </h1>
                {candidate.current_title && (
                  <p className="text-lg text-slate-600 font-medium mb-2">{candidate.current_title}</p>
                )}
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className={`${statusConfig.color} border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] px-3 py-1`}>
                    {statusConfig.label}
                  </Badge>
                  {candidate.total_experience_years !== undefined && (
                    <Badge variant="outline" className="border-2 border-black">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      {candidate.total_experience_years}+ years
                    </Badge>
                  )}
                  {candidate.source && (
                    <Badge variant="outline" className="border-2 border-black">
                      {candidate.source}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right: Action Buttons */}
          <div className="flex flex-wrap gap-2">
            {isEditMode ? (
              <>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
                  disabled={updateMutation.isPending || !hasUnsavedChanges}
                  className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black bg-green-600 hover:bg-green-700 text-white"
                >
                  {updateMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-2" />
                  )}
                  Save Changes
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={exitEditMode}
                  disabled={updateMutation.isPending}
                  className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                >
                  Cancel
                </Button>
              </>
            ) : !isReviewMode ? (
              <>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => navigate(`/candidates/${id}/matches`)}
                  className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                >
                  <Target className="h-4 w-4 mr-2" />
                  Matches
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={enterEditMode}
                  className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                >
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAssignmentDialog(true)}
                  className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                >
                  <UserPlus className="h-4 w-4 mr-2" />
                  {currentAssignment ? 'Reassign' : 'Assign'}
                </Button>
                {candidate.resume_file_url && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownloadResume}
                      className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Resume
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleReparse}
                      disabled={reparseMutation.isPending}
                      className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                    >
                      {reparseMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4 mr-2" />
                      )}
                      Re-parse
                    </Button>
                  </>
                )}
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowDeleteDialog(true)}
                  className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Information */}
        <div className="lg:col-span-2 space-y-6">
          {/* Contact Information */}
          <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <CardHeader className="bg-slate-50">
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-primary" />
                Contact Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isEditMode ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData?.email || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('email', e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                      id="phone"
                      value={formData?.phone || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('phone', e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="location">Location</Label>
                    <Input
                      id="location"
                      value={formData?.location || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('location', e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="linkedin">LinkedIn URL</Label>
                    <Input
                      id="linkedin"
                      value={formData?.linkedin_url || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('linkedin_url', e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="portfolio">Portfolio URL</Label>
                    <Input
                      id="portfolio"
                      value={formData?.portfolio_url || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('portfolio_url', e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {candidate.email && (
                    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded border-2 border-black">
                      <Mail className="h-5 w-5 text-slate-600 flex-shrink-0" />
                      <a
                        href={`mailto:${candidate.email}`}
                        className="text-sm font-medium hover:underline text-slate-900 truncate"
                      >
                        {candidate.email}
                      </a>
                    </div>
                  )}
                  {candidate.phone && (
                    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded border-2 border-black">
                      <Phone className="h-5 w-5 text-slate-600 flex-shrink-0" />
                      <a
                        href={`tel:${candidate.phone}`}
                        className="text-sm font-medium hover:underline text-slate-900"
                      >
                        {candidate.phone}
                      </a>
                    </div>
                  )}
                  {candidate.location && (
                    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded border-2 border-black">
                      <MapPin className="h-5 w-5 text-slate-600 flex-shrink-0" />
                      <span className="text-sm font-medium text-slate-900">{candidate.location}</span>
                    </div>
                  )}
                  {candidate.linkedin_url && (
                    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded border-2 border-black">
                      <Linkedin className="h-5 w-5 text-slate-600 flex-shrink-0" />
                      <a
                        href={candidate.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium hover:underline text-blue-600 truncate"
                      >
                        LinkedIn Profile
                      </a>
                    </div>
                  )}
                  {candidate.portfolio_url && (
                    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded border-2 border-black">
                      <Globe className="h-5 w-5 text-slate-600 flex-shrink-0" />
                      <a
                        href={candidate.portfolio_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium hover:underline text-blue-600 truncate"
                      >
                        Portfolio
                      </a>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Professional Summary */}
          {(candidate.professional_summary || isEditMode) && (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-gradient-to-r from-primary/5 to-secondary/5">
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Professional Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isEditMode ? (
                  <Textarea
                    value={formData?.professional_summary || ''}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => updateField('professional_summary', e.target.value)}
                    className="min-h-[150px] border-2 border-black"
                    placeholder="Enter professional summary..."
                  />
                ) : (
                  <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {candidate.professional_summary}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Work Experience */}
          {(candidate.work_experience && candidate.work_experience.length > 0) || isEditMode ? (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-slate-50">
                <CardTitle className="flex items-center gap-2">
                  <Briefcase className="h-5 w-5 text-primary" />
                  Work Experience
                </CardTitle>
                {!isEditMode && (
                  <CardDescription>
                    {candidate.work_experience?.length || 0} position{(candidate.work_experience?.length || 0) !== 1 ? 's' : ''}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                {isEditMode ? (
                  <WorkExperienceEditor
                    value={(formData?.work_experience || []).map((exp) => ({
                      ...exp,
                      location: exp.location ?? undefined,
                      start_date: exp.start_date ?? undefined,
                      end_date: exp.end_date ?? undefined,
                      description: exp.description ?? '',
                      duration_months: exp.duration_months ?? undefined,
                    }))}
                    onChange={(exp) => updateField('work_experience', exp)}
                  />
                ) : (
                  <div className="space-y-6">
                    {candidate.work_experience.map((exp, index) => (
                      <div key={index}>
                        {index > 0 && <Separator className="my-6" />}
                        <div className="space-y-3">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <h4 className="font-bold text-lg text-slate-900">{exp.title}</h4>
                              <p className="text-sm font-medium text-slate-600 mt-1">
                                {exp.company}
                                {exp.location && ` • ${exp.location}`}
                              </p>
                            </div>
                            {exp.is_current && (
                              <Badge className="bg-green-500 text-white border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] flex-shrink-0">
                                Current
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Calendar className="h-4 w-4" />
                            <span className="font-medium">
                              {exp.start_date} - {exp.end_date || 'Present'}
                            </span>
                            {exp.duration_months && (
                              <span className="text-xs bg-slate-100 px-2 py-1 rounded border border-slate-300">
                                {Math.floor(exp.duration_months / 12)}y {exp.duration_months % 12}m
                              </span>
                            )}
                          </div>
                          {exp.description && (
                            <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap pl-6 border-l-2 border-primary">
                              {exp.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* Education */}
          {(candidate.education && candidate.education.length > 0) || isEditMode ? (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-slate-50">
                <CardTitle className="flex items-center gap-2">
                  <GraduationCap className="h-5 w-5 text-primary" />
                  Education
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isEditMode ? (
                  <EducationEditor
                    value={(formData?.education || []).map((edu) => ({
                      ...edu,
                      field_of_study: edu.field_of_study ?? undefined,
                      graduation_year: edu.graduation_year ?? undefined,
                      gpa: edu.gpa ?? undefined,
                    }))}
                    onChange={(edu) => updateField('education', edu)}
                  />
                ) : (
                  <div className="space-y-4">
                    {candidate.education.map((edu, index) => (
                      <div key={index}>
                        {index > 0 && <Separator className="my-4" />}
                        <div className="space-y-2">
                          <h4 className="font-bold text-lg text-slate-900">{edu.degree}</h4>
                          {edu.field_of_study && (
                            <p className="text-sm font-medium text-slate-700">{edu.field_of_study}</p>
                          )}
                          <p className="text-sm text-slate-600">{edu.institution}</p>
                          <div className="flex items-center gap-4 text-xs text-slate-500">
                            {edu.graduation_year && (
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {edu.graduation_year}
                              </span>
                            )}
                            {edu.gpa && (
                              <span className="font-medium bg-slate-100 px-2 py-0.5 rounded border border-slate-300">
                                GPA: {edu.gpa}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* Documents Section */}
          <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <CardHeader className="bg-slate-50">
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Documents
              </CardTitle>
              <CardDescription>
                {documentsResponse?.total || 0} document{documentsResponse?.total !== 1 ? 's' : ''} uploaded
              </CardDescription>
            </CardHeader>
            <CardContent>
              {documentsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : (
                <DocumentList
                  documents={documentsResponse?.documents || []}
                  loading={documentsLoading}
                  onView={handleViewDocument}
                  onDownload={handleDownloadDocument}
                  onVerify={handleVerifyDocument}
                  onDelete={handleDeleteDocument}
                  showFilters={false}
                  emptyMessage="No documents uploaded yet"
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Sidebar */}
        <div className="space-y-6">
          {/* Job Matches Preview */}
          {!isReviewMode && matchesData && matchesData.total_matches > 0 && (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] bg-gradient-to-br from-primary/5 to-secondary/5">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5 text-primary" />
                    Top Matches
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(`/candidates/${id}/matches`)}
                    className="text-primary hover:text-primary"
                  >
                    All ({matchesData.total_matches})
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {matchesData.matches.slice(0, 3).map((match) => (
                  <div
                    key={match.id}
                    className="p-3 bg-white rounded border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px] cursor-pointer transition-all"
                    onClick={() => navigate(`/candidates/${id}/matches`)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h4
                          title={match.job?.title ?? match.job_posting?.title}
                          className="font-bold text-sm truncate text-slate-900"
                        >
                          {match.job?.title ?? match.job_posting?.title ?? 'Untitled job'}
                        </h4>
                        <p
                          title={match.job?.company ?? match.job_posting?.company}
                          className="text-xs text-slate-600 truncate"
                        >
                          {match.job?.company ?? match.job_posting?.company ?? 'Unknown company'}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1 flex-shrink-0">
                        <Badge
                          className={`font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${match.match_grade === 'A+' || match.match_grade === 'A'
                            ? 'bg-green-500 text-white'
                            : match.match_grade === 'B'
                              ? 'bg-yellow-500 text-white'
                              : 'bg-slate-500 text-white'
                            }`}
                        >
                          {match.match_grade}
                        </Badge>
                        <span className="text-xs font-bold text-slate-900">
                          {Math.round(match.match_score ?? 0)}%
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {match.matched_skills?.slice(0, 3).map((skill, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs border border-black">
                          {skill}
                        </Badge>
                      ))}
                      {(match.matched_skills?.length || 0) > 3 && (
                        <span className="text-xs text-slate-500 self-center font-medium">
                          +{(match.matched_skills?.length || 0) - 3}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Professional Details */}
          <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <CardHeader className="bg-slate-50">
              <CardTitle>Professional Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isEditMode ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="experience">Total Experience (Years)</Label>
                    <Input
                      id="experience"
                      type="number"
                      min="0"
                      max="70"
                      value={formData?.total_experience_years ?? ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('total_experience_years', e.target.value ? parseInt(e.target.value) : null)}
                      className="border-2 border-black"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="notice">Notice Period</Label>
                    <Input
                      id="notice"
                      value={formData?.notice_period || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('notice_period', e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="salary">Expected Salary</Label>
                    <Input
                      id="salary"
                      value={formData?.expected_salary || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateField('expected_salary', e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>
                </>
              ) : (
                <>
                  {candidate.total_experience_years !== undefined && (
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded border border-slate-200">
                      <span className="text-sm font-medium text-slate-600">Experience</span>
                      <span className="text-sm font-bold text-slate-900">
                        {candidate.total_experience_years} years
                      </span>
                    </div>
                  )}
                  {candidate.notice_period && (
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded border border-slate-200">
                      <span className="text-sm font-medium text-slate-600 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Notice Period
                      </span>
                      <span className="text-sm font-bold text-slate-900">
                        {candidate.notice_period}
                      </span>
                    </div>
                  )}
                  {candidate.expected_salary && (
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded border-2 border-green-500">
                      <span className="text-sm font-medium text-green-700 flex items-center gap-1">
                        <DollarSign className="h-3 w-3" />
                        Expected Salary
                      </span>
                      <span className="text-sm font-bold text-green-700">
                        {candidate.expected_salary}
                      </span>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Skills */}
          {(candidate.skills && candidate.skills.length > 0) || isEditMode ? (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-gradient-to-r from-primary/10 to-secondary/10">
                <CardTitle className="text-base">Skills</CardTitle>
              </CardHeader>
              <CardContent>
                {isEditMode ? (
                  <div className="space-y-2">
                    <Label htmlFor="skills">Skills</Label>
                    <TagInput
                      value={formData?.skills || []}
                      onChange={(skills) => updateField('skills', skills)}
                      placeholder="Add a skill (e.g., React, Python)..."
                    />
                    <p className="text-xs text-slate-500">
                      Press Enter or blur to add a skill. Click X to remove.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {candidate.skills.map((skill, index) => (
                      <Badge
                        key={index}
                        className="bg-primary text-primary-foreground border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                      >
                        {skill}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* Certifications */}
          {(candidate.certifications && candidate.certifications.length > 0) || isEditMode ? (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-slate-50">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Award className="h-5 w-5 text-yellow-600" />
                  Certifications
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isEditMode ? (
                  <div className="space-y-2">
                    <TagInput
                      value={formData?.certifications || []}
                      onChange={(certs) => updateField('certifications', certs)}
                      placeholder="Add certification..."
                    />
                    <p className="text-xs text-slate-500">
                      Press Enter to add.
                    </p>
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {candidate.certifications.map((cert, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm">
                        <span className="text-yellow-600 mt-0.5">•</span>
                        <span className="text-slate-700">{cert}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* Languages */}
          {(candidate.languages && candidate.languages.length > 0) || isEditMode ? (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-slate-50">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Languages className="h-5 w-5 text-blue-600" />
                  Languages
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isEditMode ? (
                  <div className="space-y-2">
                    <TagInput
                      value={formData?.languages || []}
                      onChange={(langs) => updateField('languages', langs)}
                      placeholder="Add language..."
                    />
                    <p className="text-xs text-slate-500">
                      Press Enter to add.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {candidate.languages.map((lang, index) => (
                      <Badge key={index} variant="outline" className="border-2 border-black">
                        {lang}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* Preferred Locations */}
          {(candidate.preferred_locations && candidate.preferred_locations.length > 0) || isEditMode ? (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-slate-50">
                <CardTitle className="flex items-center gap-2 text-base">
                  <MapPin className="h-5 w-5 text-red-600" />
                  Preferred Locations
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isEditMode ? (
                  <div className="space-y-2">
                    <TagInput
                      value={formData?.preferred_locations || []}
                      onChange={(locs) => updateField('preferred_locations', locs)}
                      placeholder="Add location..."
                    />
                    <p className="text-xs text-slate-500">
                      Press Enter to add.
                    </p>
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {candidate.preferred_locations.map((loc, index) => (
                      <li key={index} className="flex items-center gap-2 text-sm">
                        <MapPin className="h-3 w-3 text-slate-400" />
                        <span className="text-slate-700">{loc}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* Preferred Roles */}
          <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50">
              <CardTitle className="flex items-center gap-2 text-base">
                <Star className="h-5 w-5 text-purple-600" />
                Preferred Roles
              </CardTitle>
              <CardDescription>
                Manually specify desired job roles (max 10)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <TagInput
                  value={preferredRoles}
                  onChange={handleUpdatePreferredRoles}
                  placeholder="Add preferred role (e.g., Software Engineer)..."
                  disabled={updatePreferredRolesMutation.isPending}
                />
                <p className="text-xs text-slate-500">
                  {preferredRoles.length}/10 roles • Press Enter to add, click X to remove
                </p>
                {updatePreferredRolesMutation.isPending && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Saving...</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* AI-Suggested Roles */}
          <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] bg-gradient-to-br from-blue-50 to-purple-50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Sparkles className="h-5 w-5 text-purple-600" />
                    AI-Suggested Roles
                  </CardTitle>
                  <CardDescription>
                    AI-generated role recommendations based on profile
                  </CardDescription>
                </div>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => generateRoleSuggestionsMutation.mutate()}
                  disabled={isGeneratingRoles || !candidate}
                  className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2 border-black"
                >
                  {isGeneratingRoles ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Generate
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {candidate?.suggested_roles ? (
                <div className="space-y-3">
                  {candidate.suggested_roles.roles.slice(0, 5).map((suggestion, index) => (
                    <div
                      key={index}
                      className="p-4 bg-white rounded border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] space-y-2"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2 flex-1">
                          <Badge
                            className="bg-purple-600 text-white border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] flex-shrink-0 font-bold"
                          >
                            #{index + 1}
                          </Badge>
                          <div>
                            <h4 className="font-bold text-sm text-slate-900">{suggestion.role}</h4>
                            <p className="text-xs text-slate-600 mt-1">{suggestion.reasoning}</p>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          <Badge
                            className={`font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${suggestion.score >= 0.8
                              ? 'bg-green-500 text-white'
                              : suggestion.score >= 0.6
                                ? 'bg-yellow-500 text-white'
                                : 'bg-slate-500 text-white'
                              }`}
                          >
                            {(suggestion.score * 100).toFixed(0)}%
                          </Badge>
                          <span className="text-xs text-slate-500">match</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  <div className="text-xs text-slate-500 text-center pt-2">
                    Generated {new Date(candidate.suggested_roles.generated_at).toLocaleString()} • {candidate.suggested_roles.model_version}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <Sparkles className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                  <p className="text-sm font-medium">No AI suggestions yet</p>
                  <p className="text-xs mt-1">Click "Generate" to get role recommendations</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Current Assignment */}

          {currentAssignment && (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] bg-blue-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Users className="h-5 w-5 text-blue-600" />
                  Current Assignment
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between items-start">
                  <span className="text-slate-600">Assigned To</span>
                  <span className="font-bold text-slate-900 text-right">{currentAssignment.assigned_to?.full_name}</span>
                </div>
                <div className="flex justify-between items-start">
                  <span className="text-slate-600">Role</span>
                  <span className="text-slate-900">{currentAssignment.assigned_to?.roles?.[0]?.name || 'N/A'}</span>
                </div>
                <div className="flex justify-between items-start">
                  <span className="text-slate-600">Email</span>
                  <span className="text-slate-900 text-xs">{currentAssignment.assigned_to?.email}</span>
                </div>
                <Separator />
                <div className="flex justify-between items-start">
                  <span className="text-slate-600">Assigned By</span>
                  <span className="text-slate-900">
                    {currentAssignment.assigned_by
                      ? `${currentAssignment.assigned_by.first_name} ${currentAssignment.assigned_by.last_name}`
                      : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-start">
                  <span className="text-slate-600">Date</span>
                  <span className="text-slate-900">
                    {new Date(currentAssignment.created_at).toLocaleDateString()}
                  </span>
                </div>
                {currentAssignment.assignment_reason && (
                  <>
                    <Separator />
                    <div>
                      <span className="text-slate-600 block mb-1">Reason:</span>
                      <p className="text-slate-900">{currentAssignment.assignment_reason}</p>
                    </div>
                  </>
                )}
                <Badge
                  className={`mt-2 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${currentAssignment.status === 'ACTIVE' ? 'bg-yellow-500 text-white' : 'bg-green-500 text-white'
                    }`}
                >
                  {currentAssignment.status}
                </Badge>
              </CardContent>
            </Card>
          )}

          {/* Resume Info */}
          {candidate.resume_uploaded_at && (
            <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <CardHeader className="bg-slate-50">
                <CardTitle className="text-base">Resume Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Uploaded</span>
                  <span className="font-medium text-slate-900">
                    {new Date(candidate.resume_uploaded_at).toLocaleDateString()}
                  </span>
                </div>
                {candidate.resume_parsed_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-600">Parsed</span>
                    <span className="font-medium text-slate-900">
                      {new Date(candidate.resume_parsed_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Candidate</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this candidate? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reject Confirmation Dialog (Review Mode) */}
      <AlertDialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Candidate</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to reject this candidate? They will be removed from the review queue.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setRejectReason('')}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => rejectMutation.mutate()}
              className="bg-red-600 hover:bg-red-700"
            >
              Reject Candidate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Assignment Dialog */}
      {showAssignmentDialog && (
        <CandidateAssignmentDialog
          open={showAssignmentDialog}
          onOpenChange={setShowAssignmentDialog}
          candidateId={Number(id)}
          candidateName={candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
        />
      )}

      {/* Document Viewer */}
      {showDocumentViewer && selectedDocument && (
        <DocumentViewer
          document={selectedDocument}
          open={showDocumentViewer}
          onClose={() => {
            setShowDocumentViewer(false);
            setSelectedDocument(null);
          }}
        />
      )}

      {/* Document Verification Modal */}
      {showVerificationModal && selectedDocument && (
        <DocumentVerificationModal
          document={selectedDocument}
          open={showVerificationModal}
          onClose={() => {
            setShowVerificationModal(false);
            setSelectedDocument(null);
          }}
          onVerified={handleDocumentVerified}
        />
      )}
    </div>
  );
}
