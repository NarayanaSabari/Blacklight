/**
 * Candidate Detail Page
 * 
 * Full profile view with:
 * - Complete candidate information display
 * - Resume viewer (PDF/DOCX)
 * - Edit mode
 * - Download resume
 * - Re-parse resume
 * - Status updates
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
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
} from 'lucide-react';
import { toast } from 'sonner';

import { candidateApi } from '@/lib/candidateApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-500',
  screening: 'bg-yellow-500',
  interviewed: 'bg-purple-500',
  offered: 'bg-orange-500',
  hired: 'bg-green-500',
  rejected: 'bg-red-500',
  withdrawn: 'bg-gray-500',
};

export function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Fetch candidate data
  const { data: candidate, isLoading, error } = useQuery({
    queryKey: ['candidate', id],
    queryFn: () => candidateApi.getCandidate(Number(id)),
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

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/candidates')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">
              {candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
            </h1>
            {candidate.current_title && (
              <p className="text-muted-foreground">{candidate.current_title}</p>
            )}
          </div>
          <Badge className={STATUS_COLORS[candidate.status]}>
            {candidate.status.toUpperCase()}
          </Badge>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/candidates/${id}/edit`)}
          >
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
          {candidate.resume_file_url && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadResume}
              >
                <Download className="h-4 w-4 mr-2" />
                Download Resume
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReparse}
                disabled={reparseMutation.isPending}
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
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* View Mode */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Contact Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Contact Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {candidate.email && (
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <a
                        href={`mailto:${candidate.email}`}
                        className="text-sm hover:underline"
                      >
                        {candidate.email}
                      </a>
                    </div>
                  )}
                  {candidate.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <a
                        href={`tel:${candidate.phone}`}
                        className="text-sm hover:underline"
                      >
                        {candidate.phone}
                      </a>
                    </div>
                  )}
                  {candidate.location && (
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{candidate.location}</span>
                    </div>
                  )}
                  {candidate.linkedin_url && (
                    <div className="flex items-center gap-2">
                      <Linkedin className="h-4 w-4 text-muted-foreground" />
                      <a
                        href={candidate.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm hover:underline"
                      >
                        LinkedIn Profile
                      </a>
                    </div>
                  )}
                  {candidate.portfolio_url && (
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                      <a
                        href={candidate.portfolio_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm hover:underline"
                      >
                        Portfolio
                      </a>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Professional Summary */}
            {candidate.professional_summary && (
              <Card>
                <CardHeader>
                  <CardTitle>Professional Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {candidate.professional_summary}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Work Experience */}
            {candidate.work_experience && candidate.work_experience.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Briefcase className="h-5 w-5" />
                    Work Experience
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {candidate.work_experience.map((exp, index) => (
                    <div key={index}>
                      {index > 0 && <Separator className="my-4" />}
                      <div className="space-y-2">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-semibold">{exp.title}</h4>
                            <p className="text-sm text-muted-foreground">
                              {exp.company}
                              {exp.location && ` • ${exp.location}`}
                            </p>
                          </div>
                          {exp.is_current && (
                            <Badge variant="secondary">Current</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          <span>
                            {exp.start_date} - {exp.end_date || 'Present'}
                            {exp.duration_months && (
                              <span className="ml-2">
                                ({Math.floor(exp.duration_months / 12)} years{' '}
                                {exp.duration_months % 12} months)
                              </span>
                            )}
                          </span>
                        </div>
                        {exp.description && (
                          <p className="text-sm text-muted-foreground mt-2 whitespace-pre-wrap">
                            {exp.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Education */}
            {candidate.education && candidate.education.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <GraduationCap className="h-5 w-5" />
                    Education
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {candidate.education.map((edu, index) => (
                    <div key={index}>
                      {index > 0 && <Separator className="my-4" />}
                      <div className="space-y-1">
                        <h4 className="font-semibold">{edu.degree}</h4>
                        {edu.field_of_study && (
                          <p className="text-sm text-muted-foreground">
                            {edu.field_of_study}
                          </p>
                        )}
                        <p className="text-sm text-muted-foreground">
                          {edu.institution}
                          {edu.graduation_year && ` • ${edu.graduation_year}`}
                        </p>
                        {edu.gpa && (
                          <p className="text-sm text-muted-foreground">
                            GPA: {edu.gpa}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Additional Info */}
          <div className="space-y-6">
            {/* Professional Details */}
            <Card>
              <CardHeader>
                <CardTitle>Professional Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {candidate.total_experience_years !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Experience</span>
                    <span className="text-sm font-medium">
                      {candidate.total_experience_years} years
                    </span>
                  </div>
                )}
                {candidate.notice_period && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Notice Period
                    </span>
                    <span className="text-sm font-medium">
                      {candidate.notice_period}
                    </span>
                  </div>
                )}
                {candidate.expected_salary && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />
                      Expected Salary
                    </span>
                    <span className="text-sm font-medium">
                      {candidate.expected_salary}
                    </span>
                  </div>
                )}
                <Separator />
                <div className="space-y-2">
                  <span className="text-sm text-muted-foreground">Source</span>
                  <div>
                    <Badge variant="outline">{candidate.source}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Skills */}
            {candidate.skills && candidate.skills.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Skills</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {candidate.skills.map((skill, index) => (
                      <Badge key={index} variant="secondary">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Certifications */}
            {candidate.certifications && candidate.certifications.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Award className="h-5 w-5" />
                    Certifications
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="list-disc list-inside space-y-1">
                    {candidate.certifications.map((cert, index) => (
                      <li key={index} className="text-sm text-muted-foreground">
                        {cert}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Languages */}
            {candidate.languages && candidate.languages.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Languages className="h-5 w-5" />
                    Languages
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {candidate.languages.map((lang, index) => (
                      <Badge key={index} variant="outline">
                        {lang}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Preferred Locations */}
            {candidate.preferred_locations && candidate.preferred_locations.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPin className="h-5 w-5" />
                    Preferred Locations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="list-disc list-inside space-y-1">
                    {candidate.preferred_locations.map((loc, index) => (
                      <li key={index} className="text-sm text-muted-foreground">
                        {loc}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Resume Info */}
            {candidate.resume_uploaded_at && (
              <Card>
                <CardHeader>
                  <CardTitle>Resume Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Uploaded</span>
                    <span>
                      {new Date(candidate.resume_uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                  {candidate.resume_parsed_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Parsed</span>
                      <span>
                        {new Date(candidate.resume_parsed_at).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Metadata */}
            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created</span>
                  <span>{new Date(candidate.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Updated</span>
                  <span>{new Date(candidate.updated_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">ID</span>
                  <span className="font-mono text-xs">{candidate.id}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Candidate</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete{' '}
              <strong>
                {candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
              </strong>
              ? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
