/**
 * Public Onboarding Page
 * Public route for candidates to complete self-onboarding via invitation token
 */

import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { CheckCircle2, AlertCircle, XCircle, ArrowRight } from 'lucide-react';
import { useVerifyInvitation } from '@/hooks/useOnboarding';
import { CandidateOnboardingFlow } from '@/components/onboarding/CandidateOnboardingFlow';

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
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
        <div className="mx-auto max-w-4xl space-y-6 pt-12">
          <Card>
            <CardHeader>
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-96" />
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
        <div className="mx-auto max-w-2xl pt-12">
          <Card>
            <CardContent className="pt-6">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Invalid Invitation</AlertTitle>
                <AlertDescription>
                  {error?.message || 'This invitation link is invalid or has expired.'}
                </AlertDescription>
              </Alert>
              <div className="mt-6 text-center">
                <p className="text-sm text-muted-foreground mb-4">
                  If you believe this is an error, please contact the recruiter who sent you this
                  invitation.
                </p>
                <Button onClick={() => navigate('/')} variant="outline">
                  Go to Homepage
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Invalid token (after data is loaded)
  if (!data.is_valid) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
        <div className="mx-auto max-w-2xl pt-12">
          <Card>
            <CardContent className="pt-6">
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Invitation Not Valid</AlertTitle>
                <AlertDescription>
                  {'This invitation is no longer valid or has expired.'}
                </AlertDescription>
              </Alert>
              <div className="mt-6 text-center">
                <Button onClick={() => navigate('/')} variant="outline">
                  Go to Homepage
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const invitation = data;
  const isAlreadySubmitted = invitation.status === 'pending_review';
  const isApproved = invitation.status === 'approved';
  const isRejected = invitation.status === 'rejected';
  const isCancelled = invitation.status === 'cancelled';

  // Already submitted
  if (isAlreadySubmitted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
        <div className="mx-auto max-w-2xl pt-12">
          <Card>
            <CardContent className="pt-6">
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertTitle>Application Submitted</AlertTitle>
                <AlertDescription>
                  Your application has been submitted and is currently under review. We will notify
                  you via email once it has been reviewed.
                </AlertDescription>
              </Alert>
              <div className="mt-6 text-center">
                <p className="text-sm text-muted-foreground">
                  Thank you for your patience. This process typically takes 2-3 business days.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Approved
  if (isApproved) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
        <div className="mx-auto max-w-2xl pt-12">
          <Card>
            <CardContent className="pt-6">
              <Alert className="border-green-600">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertTitle className="text-green-600">Application Approved!</AlertTitle>
                <AlertDescription>
                  Congratulations! Your application has been approved. You should receive further
                  instructions via email shortly.
                </AlertDescription>
              </Alert>
              <div className="mt-6 text-center">
                <p className="text-sm text-muted-foreground mb-4">
                  Welcome aboard! We're excited to have you join our team.
                </p>
                <Button onClick={() => navigate('/')}>
                  Go to Homepage
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Rejected
  if (isRejected) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
        <div className="mx-auto max-w-2xl pt-12">
          <Card>
            <CardContent className="pt-6">
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Application Not Approved</AlertTitle>
                <AlertDescription>
                  {invitation.rejection_reason ||
                    'Unfortunately, we are unable to proceed with your application at this time.'}
                </AlertDescription>
              </Alert>
              <div className="mt-6 text-center">
                <p className="text-sm text-muted-foreground">
                  Thank you for your interest. We wish you the best in your job search.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Cancelled
  if (isCancelled) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
        <div className="mx-auto max-w-2xl pt-12">
          <Card>
            <CardContent className="pt-6">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Invitation Cancelled</AlertTitle>
                <AlertDescription>
                  This invitation has been cancelled and is no longer valid.
                </AlertDescription>
              </Alert>
              <div className="mt-6 text-center">
                <p className="text-sm text-muted-foreground">
                  Please contact the recruiter if you have any questions.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Valid invitation - show onboarding flow
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6">
      <div className="pt-12">
        {/* Welcome Header */}
        <div className="mx-auto max-w-4xl mb-6 text-center">
          <h1 className="text-3xl font-bold mb-2">Welcome to Our Team!</h1>
          <p className="text-muted-foreground">
            Complete your onboarding to join us. This should take about 10 minutes.
          </p>
        </div>

        {/* Onboarding Flow */}
        <CandidateOnboardingFlow
          token={token!}
          invitation={invitation}
          onSuccess={() => {
            // Show success message or redirect
            window.location.reload();
          }}
        />
      </div>
    </div>
  );
}
