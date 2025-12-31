/**
 * Public Onboarding Page
 * Public route for candidates to complete self-onboarding via invitation token
 * Redesigned for better UX with clearer status screens and branding
 */

import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  CheckCircle2,
  AlertCircle,
  XCircle,
  Clock,
  Mail,
  FileText,
  User,
  Loader2,
  Ban,
} from 'lucide-react';
import { useVerifyInvitation } from '@/hooks/useOnboarding';
import { CandidateOnboardingFlow } from '@/components/onboarding/CandidateOnboardingFlow_v2';

// Reusable status screen component for consistent styling
function StatusScreen({
  icon: Icon,
  iconBgColor,
  iconColor,
  title,
  titleColor = 'text-slate-900',
  description,
  children,
  showHomeButton = true,
}: {
  icon: React.ElementType;
  iconBgColor: string;
  iconColor: string;
  title: string;
  titleColor?: string;
  description: string;
  children?: React.ReactNode;
  showHomeButton?: boolean;
}) {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="container mx-auto px-4 py-12 max-w-lg">
        <Card className="border-0 shadow-xl">
          <CardContent className="pt-12 pb-10">
            <div className="flex flex-col items-center text-center">
              {/* Icon */}
              <div className={`rounded-full ${iconBgColor} p-5 mb-6`}>
                <Icon className={`h-12 w-12 ${iconColor}`} />
              </div>

              {/* Title */}
              <h1 className={`text-2xl font-bold ${titleColor} mb-3`}>{title}</h1>

              {/* Description */}
              <p className="text-slate-600 leading-relaxed max-w-sm">{description}</p>

              {/* Additional content */}
              {children}

              {/* Home button */}
              {showHomeButton && (
                <Button
                  onClick={() => navigate('/')}
                  variant="outline"
                  className="mt-8"
                >
                  Go to Homepage
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Loading skeleton with better structure
function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        {/* Header skeleton */}
        <div className="text-center mb-8">
          <Skeleton className="h-10 w-64 mx-auto mb-3" />
          <Skeleton className="h-5 w-96 mx-auto" />
        </div>

        {/* Progress card skeleton */}
        <Card className="mb-6">
          <CardContent className="py-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <Skeleton className="h-6 w-48 mb-2" />
                <Skeleton className="h-4 w-24" />
              </div>
              <Skeleton className="h-8 w-16 rounded-full" />
            </div>
            <Skeleton className="h-2 w-full rounded-full mb-6" />
            <div className="flex justify-between">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex flex-col items-center gap-2">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <Skeleton className="h-3 w-16" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Form skeleton */}
        <Card>
          <CardContent className="py-8">
            <Skeleton className="h-6 w-48 mb-6" />
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-10 w-full" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-10 w-full" />
              </div>
            </div>
            <div className="mt-6 space-y-4">
              <div className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-10 w-full" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-10 w-full" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { data, isLoading, error } = useVerifyInvitation(token || '');

  useEffect(() => {
    if (!token) {
      navigate('/');
    }
  }, [token, navigate]);

  // Loading state
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  // Error state
  if (error || !data) {
    return (
      <StatusScreen
        icon={AlertCircle}
        iconBgColor="bg-red-100"
        iconColor="text-red-600"
        title="Invalid Invitation Link"
        description={error?.message || 'This invitation link is invalid or has expired. Please check your email for the correct link.'}
      >
        <div className="mt-6 p-4 bg-slate-50 rounded-lg">
          <p className="text-sm text-slate-600">
            <Mail className="inline h-4 w-4 mr-1" />
            If you believe this is an error, please contact the recruiter who sent you this invitation.
          </p>
        </div>
      </StatusScreen>
    );
  }

  // Invalid token (after data is loaded)
  if (!data.is_valid) {
    return (
      <StatusScreen
        icon={XCircle}
        iconBgColor="bg-red-100"
        iconColor="text-red-600"
        title="Invitation Expired"
        description="This invitation is no longer valid. It may have expired or been cancelled."
      >
        <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-sm text-amber-800">
            <Clock className="inline h-4 w-4 mr-1" />
            Invitations typically expire after 7 days. Please request a new invitation.
          </p>
        </div>
      </StatusScreen>
    );
  }

  const invitation = data;
  const isAlreadySubmitted = invitation.status === 'pending_review';
  const isApproved = invitation.status === 'approved';
  const isRejected = invitation.status === 'rejected';
  const isCancelled = invitation.status === 'cancelled';

  // Already submitted - Pending Review
  if (isAlreadySubmitted) {
    return (
      <StatusScreen
        icon={Clock}
        iconBgColor="bg-blue-100"
        iconColor="text-blue-600"
        title="Application Under Review"
        description="Your application has been submitted and is currently being reviewed by our team."
        showHomeButton={false}
      >
        <div className="mt-8 w-full space-y-4">
          {/* Timeline */}
          <div className="flex items-center justify-center gap-2 text-sm text-slate-600">
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span>Submitted</span>
            </div>
            <div className="h-px w-8 bg-slate-300" />
            <div className="flex items-center gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
              <span className="text-blue-600 font-medium">In Review</span>
            </div>
            <div className="h-px w-8 bg-slate-300" />
            <div className="flex items-center gap-1.5 text-slate-400">
              <div className="h-2 w-2 rounded-full bg-slate-300" />
              <span>Decision</span>
            </div>
          </div>

          {/* Info cards */}
          <div className="mt-6 grid gap-3">
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <Mail className="h-5 w-5 text-slate-500" />
              <div className="text-left">
                <p className="text-sm font-medium text-slate-700">Email Notification</p>
                <p className="text-xs text-slate-500">
                  You'll receive an email at {invitation.email} once reviewed
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <Clock className="h-5 w-5 text-slate-500" />
              <div className="text-left">
                <p className="text-sm font-medium text-slate-700">Review Time</p>
                <p className="text-xs text-slate-500">Typically 2-3 business days</p>
              </div>
            </div>
          </div>

          <p className="text-sm text-slate-500 mt-4">
            Thank you for your patience. You can safely close this page.
          </p>
        </div>
      </StatusScreen>
    );
  }

  // Approved
  if (isApproved) {
    return (
      <StatusScreen
        icon={CheckCircle2}
        iconBgColor="bg-green-100"
        iconColor="text-green-600"
        title="Congratulations!"
        titleColor="text-green-700"
        description="Your application has been approved. Welcome to the team!"
      >
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800">
            <Mail className="inline h-4 w-4 mr-1" />
            Check your email for next steps and further instructions.
          </p>
        </div>
      </StatusScreen>
    );
  }

  // Rejected
  if (isRejected) {
    return (
      <StatusScreen
        icon={XCircle}
        iconBgColor="bg-slate-100"
        iconColor="text-slate-500"
        title="Application Not Approved"
        description={
          invitation.rejection_reason ||
          'Unfortunately, we are unable to proceed with your application at this time.'
        }
      >
        <div className="mt-6 p-4 bg-slate-50 rounded-lg">
          <p className="text-sm text-slate-600">
            Thank you for your interest. We wish you the best in your job search.
          </p>
        </div>
      </StatusScreen>
    );
  }

  // Cancelled
  if (isCancelled) {
    return (
      <StatusScreen
        icon={Ban}
        iconBgColor="bg-amber-100"
        iconColor="text-amber-600"
        title="Invitation Cancelled"
        description="This invitation has been cancelled and is no longer valid."
      >
        <div className="mt-6 p-4 bg-slate-50 rounded-lg">
          <p className="text-sm text-slate-600">
            <Mail className="inline h-4 w-4 mr-1" />
            Please contact the recruiter if you have any questions.
          </p>
        </div>
      </StatusScreen>
    );
  }

  // Valid invitation - show onboarding flow
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="container mx-auto px-4 py-8 md:py-12">
        {/* Welcome Header */}
        <div className="max-w-4xl mx-auto mb-8 text-center">
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-3">
            Welcome, {invitation.first_name || 'there'}!
          </h1>
          <p className="text-lg text-slate-600 max-w-xl mx-auto">
            Complete your profile to join our talent network. This takes about 10 minutes.
          </p>

          {/* Quick info badges */}
          <div className="flex items-center justify-center gap-4 mt-6 flex-wrap">
            <div className="flex items-center gap-1.5 text-sm text-slate-600">
              <FileText className="h-4 w-4" />
              <span>5 quick steps</span>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-slate-600">
              <Clock className="h-4 w-4" />
              <span>~10 minutes</span>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-slate-600">
              <User className="h-4 w-4" />
              <span>AI-assisted</span>
            </div>
          </div>
        </div>

        {/* Onboarding Flow */}
        <CandidateOnboardingFlow
          token={token!}
          invitation={invitation}
          onSuccess={() => {
            window.location.reload();
          }}
        />
      </div>
    </div>
  );
}
