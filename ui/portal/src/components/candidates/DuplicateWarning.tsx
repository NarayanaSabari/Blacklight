import { useQuery } from '@tanstack/react-query';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, User, Mail, ExternalLink } from 'lucide-react';
import { candidateApi } from '@/lib/candidateApi';
import { Skeleton } from '@/components/ui/skeleton';
import { Link } from 'react-router-dom';

interface DuplicateWarningProps {
  firstName?: string;
  lastName?: string;
  email?: string;
  excludeCandidateId?: number;
}

export function DuplicateWarning({
  firstName,
  lastName,
  email,
  excludeCandidateId,
}: DuplicateWarningProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['duplicate-check', firstName, lastName, email, excludeCandidateId],
    queryFn: () =>
      candidateApi.checkDuplicates({
        first_name: firstName,
        last_name: lastName,
        email: email,
        exclude_candidate_id: excludeCandidateId,
      }),
    enabled: !!(firstName || email),
    staleTime: 0,
  });

  if (isLoading) {
    return <Skeleton className="h-20 w-full" />;
  }

  if (!data || data.count === 0) {
    return null;
  }

  const { duplicates, count } = data;

  return (
    <Alert variant="destructive" className="border-2 border-red-500 bg-red-50">
      <AlertTriangle className="h-5 w-5" />
      <AlertDescription className="ml-2">
        <div className="space-y-3">
          <div>
            <p className="font-bold text-red-900">
              Potential Duplicate Detected ({count} {count === 1 ? 'match' : 'matches'})
            </p>
            <p className="text-sm text-red-700 mt-1">
              This candidate may already exist in the system. Please review before approving.
            </p>
          </div>

          <div className="space-y-2">
            {duplicates.map((dup, index) => (
              <div
                key={dup.candidate.id || index}
                className="bg-white border border-red-200 rounded-lg p-3 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-slate-600" />
                      <span className="font-semibold text-slate-900">
                        {dup.candidate.first_name} {dup.candidate.last_name}
                      </span>
                      <Badge
                        variant="outline"
                        className="text-xs border-slate-300 text-slate-600"
                      >
                        {dup.candidate.status?.replace(/_/g, ' ')}
                      </Badge>
                    </div>

                    {dup.candidate.email && (
                      <div className="flex items-center gap-2 text-sm text-slate-600">
                        <Mail className="h-3 w-3" />
                        <span>{dup.candidate.email}</span>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-1 mt-1">
                      {dup.match_reasons.map((reason) => (
                        <Badge
                          key={reason}
                          variant={reason === 'email' ? 'destructive' : 'secondary'}
                          className="text-xs"
                        >
                          {reason === 'email' ? 'Same Email' : reason === 'full_name' ? 'Same Name' : reason}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Link
                    to={`/candidates/${dup.candidate.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    View
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </AlertDescription>
    </Alert>
  );
}
