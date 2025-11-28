/**
 * Resume Viewer Component
 * Displays uploaded resume in an iframe for cross-checking during editing
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileText, Download, ExternalLink, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { env } from '@/lib/env';

interface ResumeViewerProps {
  resumeUrl?: string | null;
  resumeFileName?: string;
  candidateName?: string;
}

export function ResumeViewer({ resumeUrl, resumeFileName, candidateName }: ResumeViewerProps) {
  const [loadError, setLoadError] = useState(false);

  if (!resumeUrl) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-5 w-5" />
            Resume Preview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No resume file uploaded for this candidate.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // Construct full URL - if it's a relative path, prepend the API base URL
  const fullResumeUrl = resumeUrl.startsWith('http') ? resumeUrl : `${env.apiBaseUrl}${resumeUrl}`;

  // Strip query params for extension detection (signed URLs have query string)
  const urlPath = fullResumeUrl.split('?')[0];
  const isPDF = urlPath.toLowerCase().endsWith('.pdf');
  const isDocx = urlPath.toLowerCase().endsWith('.docx');

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = fullResumeUrl;
    link.download = resumeFileName || 'resume.pdf';
    link.target = '_blank'; // Open in new tab to trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleOpenInNew = () => {
    window.open(fullResumeUrl, '_blank');
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-5 w-5" />
            Resume Preview
          </CardTitle>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleOpenInNew}
              className="gap-2"
            >
              <ExternalLink className="h-4 w-4" />
              Open
            </Button>
          </div>
        </div>
        {resumeFileName && (
          <p className="text-sm text-muted-foreground">{resumeFileName}</p>
        )}
      </CardHeader>
      <CardContent className="flex-1 p-0">
        {loadError ? (
          <div className="p-6">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Unable to display resume preview.{' '}
                <button
                  onClick={handleOpenInNew}
                  className="underline font-medium"
                >
                  Click here to open in a new tab
                </button>
              </AlertDescription>
            </Alert>
          </div>
        ) : isPDF ? (
          <iframe
            src={fullResumeUrl}
            className="w-full h-full min-h-[600px] border-0"
            title={`Resume - ${candidateName || 'Candidate'}`}
            onError={() => setLoadError(true)}
          />
        ) : isDocx ? (
          <div className="p-6 h-full flex flex-col items-center justify-center bg-muted/30">
            <FileText className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground text-center mb-4">
              Word documents cannot be previewed directly in the browser.
            </p>
            <div className="flex gap-2">
              <Button onClick={handleDownload} size="sm" className="gap-2">
                <Download className="h-4 w-4" />
                Download to View
              </Button>
              <Button onClick={handleOpenInNew} variant="outline" size="sm" className="gap-2">
                <ExternalLink className="h-4 w-4" />
                Open in New Tab
              </Button>
            </div>
          </div>
        ) : (
          <div className="p-6">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Preview not available for this file type.{' '}
                <button
                  onClick={handleDownload}
                  className="underline font-medium"
                >
                  Download to view
                </button>
              </AlertDescription>
            </Alert>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
