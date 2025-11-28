/**
 * Split-Screen Candidate Review Component
 * Enhanced review interface with list + detail panels
 */

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
    CheckCircle2,
    XCircle,
    AlertCircle,
    Loader2,
    Mail,
    Upload,
    Eye,
    Clock,
    MapPin,
    Briefcase,
    ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';
import { candidateApi } from '@/lib/candidateApi';
import { invitationApi } from '@/lib/api/invitationApi';
import { cn } from '@/lib/utils';
import type { Candidate, CandidateUpdateInput } from '@/types/candidate';
import type { InvitationWithRelations } from '@/types/invitation';

interface SplitScreenReviewProps {
    pendingReviewCandidates?: Candidate[];
    submittedInvitations?: InvitationWithRelations[];
    isLoadingCandidates?: boolean;
    isLoadingInvitations?: boolean;
}

type ReviewCandidate = Candidate | InvitationWithRelations;

const isCandidateType = (item: ReviewCandidate): item is Candidate => {
    return 'status' in item; // Candidate objects include 'status' field reliably
};

export function SplitScreenReview({
    pendingReviewCandidates = [],
    submittedInvitations = [],
    isLoadingCandidates,
    isLoadingInvitations,
}: SplitScreenReviewProps) {
    const queryClient = useQueryClient();
    const navigate = useNavigate();

    // Combine both lists
    const allItems: ReviewCandidate[] = [...pendingReviewCandidates, ...submittedInvitations];

    const [selectedIndex, setSelectedIndex] = useState(0);
    const [isEditing, setIsEditing] = useState(false);

    // Form state for editing
    const selectedItem = allItems[selectedIndex];
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [currentTitle, setCurrentTitle] = useState('');
    const [location, setLocation] = useState('');
    const [skills, setSkills] = useState('');
    const [summary, setSummary] = useState('');

    // Initialize form when selection changes
    useEffect(() => {
        if (!selectedItem) return;

        setFirstName(selectedItem.first_name || '');
        setLastName(selectedItem.last_name || '');
        setEmail(selectedItem.email || '');

        if (isCandidateType(selectedItem)) {
            setPhone(selectedItem.phone || '');
            setCurrentTitle(selectedItem.current_title || '');
            setLocation(selectedItem.location || '');
            setSkills((selectedItem.skills || []).join(', '));
            setSummary(selectedItem.professional_summary || '');
        } else {
            setPhone('');
            setCurrentTitle('');
            setLocation('');
            setSkills('');
            setSummary('');
        }

        setIsEditing(false);
    }, [selectedItem]);

    // Keyboard navigation
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowUp' && selectedIndex > 0) {
                e.preventDefault();
                setSelectedIndex(prev => prev - 1);
            } else if (e.key === 'ArrowDown' && selectedIndex < allItems.length - 1) {
                e.preventDefault();
                setSelectedIndex(prev => prev + 1);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [selectedIndex, allItems.length]);

    // Approve candidate mutation
    const approveCandidateMutation = useMutation({
        mutationFn: async (candidateId: number) => {
            if (isEditing && isCandidateType(selectedItem)) {
                // Save edits first
                const updatedData: Partial<CandidateUpdateInput> = {
                    first_name: firstName,
                    last_name: lastName,
                    email: email || undefined,
                    phone: phone || undefined,
                    current_title: currentTitle || undefined,
                    location: location || undefined,
                    skills: skills ? skills.split(',').map(s => s.trim()).filter(Boolean) : undefined,
                    professional_summary: summary || undefined,
                };
                await candidateApi.reviewCandidate(candidateId, updatedData);
            }
            return candidateApi.approveCandidate(candidateId);
        },
        onSuccess: () => {
            toast.success('Candidate approved!');
            queryClient.invalidateQueries({ queryKey: ['candidates-pending-review'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
            // Move to next candidate
            if (selectedIndex < allItems.length - 1) {
                setSelectedIndex(prev => prev + 1);
            } else if (selectedIndex > 0) {
                setSelectedIndex(prev => prev - 1);
            }
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Failed to approve candidate');
        },
    });

    // Approve invitation mutation
    const approveInvitationMutation = useMutation({
        mutationFn: (invitationId: number) => invitationApi.approve(invitationId),
        onSuccess: () => {
            toast.success('Invitation approved and candidate created');
            queryClient.invalidateQueries({ queryKey: ['submitted-invitations'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
            // Move to next
            if (selectedIndex < allItems.length - 1) {
                setSelectedIndex(prev => prev + 1);
            } else if (selectedIndex > 0) {
                setSelectedIndex(prev => prev - 1);
            }
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Failed to approve invitation');
        },
    });

    // Reject candidate mutation
    const rejectCandidateMutation = useMutation({
        mutationFn: (candidateId: number) => candidateApi.deleteCandidate(candidateId),
        onSuccess: () => {
            toast.success('Candidate rejected and removed');
            queryClient.invalidateQueries({ queryKey: ['candidates-pending-review'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
            // Move to next
            if (selectedIndex < allItems.length - 1) {
                setSelectedIndex(prev => prev + 1);
            } else if (selectedIndex > 0) {
                setSelectedIndex(prev => prev - 1);
            }
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Failed to reject candidate');
        },
    });

    // Reject invitation mutation
    const rejectInvitationMutation = useMutation({
        mutationFn: (invitationId: number) =>
            invitationApi.reject(invitationId, { rejection_reason: 'Not qualified' }),
        onSuccess: () => {
            toast.success('Invitation rejected');
            queryClient.invalidateQueries({ queryKey: ['submitted-invitations'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
            // Move to next
            if (selectedIndex < allItems.length - 1) {
                setSelectedIndex(prev => prev + 1);
            } else if (selectedIndex > 0) {
                setSelectedIndex(prev => prev - 1);
            }
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Failed to reject invitation');
        },
    });

    const handleApprove = () => {
        if (!selectedItem) return;

        if (isCandidateType(selectedItem)) {
            approveCandidateMutation.mutate(selectedItem.id);
        } else {
            approveInvitationMutation.mutate(selectedItem.id);
        }
    };

    const handleReject = () => {
        if (!selectedItem) return;

        if (!confirm('Are you sure you want to reject this candidate?')) return;

        if (isCandidateType(selectedItem)) {
            rejectCandidateMutation.mutate(selectedItem.id);
        } else {
            rejectInvitationMutation.mutate(selectedItem.id);
        }
    };

    const isLoading =
        approveCandidateMutation.isPending ||
        approveInvitationMutation.isPending ||
        rejectCandidateMutation.isPending ||
        rejectInvitationMutation.isPending;

    // Loading state
    if (isLoadingCandidates || isLoadingInvitations) {
        return (
            <div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-4">
                <Skeleton className="h-[600px]" />
                <Skeleton className="h-[600px]" />
            </div>
        );
    }

    // Empty state
    if (allItems.length === 0) {
        return (
            <Card className="border-2 border-dashed border-slate-300">
                <CardContent className="flex flex-col items-center justify-center py-16">
                    <div className="rounded-full bg-green-100 p-6 mb-4">
                        <CheckCircle2 className="h-16 w-16 text-green-600" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 mb-2">All Caught Up!</h3>
                    <p className="text-base text-slate-600 text-center max-w-md">
                        No candidates pending review at the moment.<br />
                        New resume uploads and email submissions will appear here.
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-4">
            {/* Left Panel - Candidate List */}
            <Card className="border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] h-[700px] overflow-hidden flex flex-col">
                <CardHeader className="bg-slate-50 border-b-2 border-black">
                    <CardTitle className="text-lg font-bold flex items-center justify-between">
                        <span>Candidates ({allItems.length})</span>
                        <Badge className="border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                            {selectedIndex + 1} / {allItems.length}
                        </Badge>
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0 overflow-y-auto flex-1">
                    <div className="divide-y-2 divide-slate-200">
                        {allItems.map((item, index) => {
                            const isCandidate = isCandidateType(item);
                            const isSelected = index === selectedIndex;

                            return (
                                <button
                                    key={`${isCandidate ? 'candidate' : 'invitation'}-${item.id}`}
                                    onClick={() => setSelectedIndex(index)}
                                    className={cn(
                                        'w-full text-left p-4 transition-all hover:bg-slate-50',
                                        isSelected && 'bg-primary/10 border-l-4 border-l-primary'
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex-1 min-w-0">
                                            <div className="font-semibold text-slate-900 truncate">
                                                {item.first_name} {item.last_name}
                                            </div>
                                            <div className="text-sm text-slate-600 truncate mt-1">
                                                {item.email}
                                            </div>
                                            <div className="flex items-center gap-2 mt-2">
                                                <Badge
                                                    variant="outline"
                                                    className={cn(
                                                        "text-xs border-2 border-black",
                                                        isCandidate ? "bg-yellow-50" : "bg-blue-50"
                                                    )}
                                                >
                                                    {isCandidate ? (
                                                        <><Upload className="h-3 w-3 mr-1" />Resume</>
                                                    ) : (
                                                        <><Mail className="h-3 w-3 mr-1" />Email</>
                                                    )}
                                                </Badge>
                                                {isCandidate && item.resume_parsed_at && (
                                                    <span className="text-xs text-slate-500 flex items-center gap-1">
                                                        <Clock className="h-3 w-3" />
                                                        {new Date(item.resume_parsed_at).toLocaleDateString()}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        {isSelected && (
                                            <ChevronRight className="h-5 w-5 text-primary flex-shrink-0" />
                                        )}
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Right Panel - Candidate Details */}
            <Card className="border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] h-[700px] overflow-hidden flex flex-col">
                <CardHeader className="bg-gradient-to-r from-primary/5 to-secondary/5 border-b-2 border-black">
                    <div className="flex items-start justify-between">
                        <div>
                            <CardTitle className="text-2xl font-bold">
                                {selectedItem?.first_name} {selectedItem?.last_name}
                            </CardTitle>
                            <p className="text-sm text-slate-600 mt-1">{selectedItem?.email}</p>
                        </div>
                        <div className="flex gap-2">
                            {isCandidateType(selectedItem) && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => navigate(`/candidates/${selectedItem.id}`)}
                                    className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                                >
                                    <Eye className="h-4 w-4 mr-2" />
                                    Full Profile
                                </Button>
                            )}
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* Edit Toggle */}
                    {isCandidateType(selectedItem) && (
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-slate-700">Candidate Information</h3>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setIsEditing(!isEditing)}
                                className="border-2 border-black"
                            >
                                {isEditing ? 'View Mode' : 'Edit Mode'}
                            </Button>
                        </div>
                    )}

                    {isEditing && isCandidateType(selectedItem) ? (
                        /* Edit Mode */
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label htmlFor="firstName">First Name *</Label>
                                    <Input
                                        id="firstName"
                                        value={firstName}
                                        onChange={(e) => setFirstName(e.target.value)}
                                        className="border-2 border-black"
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="lastName">Last Name</Label>
                                    <Input
                                        id="lastName"
                                        value={lastName}
                                        onChange={(e) => setLastName(e.target.value)}
                                        className="border-2 border-black"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label htmlFor="email">Email</Label>
                                    <Input
                                        id="email"
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="border-2 border-black"
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="phone">Phone</Label>
                                    <Input
                                        id="phone"
                                        value={phone}
                                        onChange={(e) => setPhone(e.target.value)}
                                        className="border-2 border-black"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label htmlFor="currentTitle">Current Title</Label>
                                    <Input
                                        id="currentTitle"
                                        value={currentTitle}
                                        onChange={(e) => setCurrentTitle(e.target.value)}
                                        className="border-2 border-black"
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="location">Location</Label>
                                    <Input
                                        id="location"
                                        value={location}
                                        onChange={(e) => setLocation(e.target.value)}
                                        className="border-2 border-black"
                                    />
                                </div>
                            </div>

                            <div>
                                <Label htmlFor="skills">Skills (comma-separated)</Label>
                                <Textarea
                                    id="skills"
                                    value={skills}
                                    onChange={(e) => setSkills(e.target.value)}
                                    className="border-2 border-black"
                                    rows={2}
                                />
                            </div>

                            <div>
                                <Label htmlFor="summary">Professional Summary</Label>
                                <Textarea
                                    id="summary"
                                    value={summary}
                                    onChange={(e) => setSummary(e.target.value)}
                                    className="border-2 border-black"
                                    rows={3}
                                />
                            </div>

                            <Alert className="bg-blue-50 border-2 border-blue-500">
                                <AlertCircle className="h-4 w-4 text-blue-600" />
                                <AlertDescription className="text-sm text-blue-800">
                                    Changes will be saved when you click "Approve". Click "View Mode" to discard edits.
                                </AlertDescription>
                            </Alert>
                        </div>
                    ) : (
                        /* View Mode */
                        <div className="space-y-6">
                            {isCandidateType(selectedItem) && (
                                <>
                                    {selectedItem.current_title && (
                                        <div className="flex items-start gap-3">
                                            <Briefcase className="h-5 w-5 text-slate-400 mt-0.5" />
                                            <div>
                                                <div className="text-sm font-medium text-slate-600">Current Title</div>
                                                <div className="text-base text-slate-900">{selectedItem.current_title}</div>
                                            </div>
                                        </div>
                                    )}

                                    {selectedItem.location && (
                                        <div className="flex items-start gap-3">
                                            <MapPin className="h-5 w-5 text-slate-400 mt-0.5" />
                                            <div>
                                                <div className="text-sm font-medium text-slate-600">Location</div>
                                                <div className="text-base text-slate-900">{selectedItem.location}</div>
                                            </div>
                                        </div>
                                    )}

                                    {selectedItem.phone && (
                                        <div className="flex items-start gap-3">
                                            <Mail className="h-5 w-5 text-slate-400 mt-0.5" />
                                            <div>
                                                <div className="text-sm font-medium text-slate-600">Phone</div>
                                                <div className="text-base text-slate-900">{selectedItem.phone}</div>
                                            </div>
                                        </div>
                                    )}

                                    {selectedItem.skills && selectedItem.skills.length > 0 && (
                                        <div>
                                            <div className="text-sm font-medium text-slate-600 mb-2">Skills</div>
                                            <div className="flex flex-wrap gap-2">
                                                {selectedItem.skills.map((skill, idx) => (
                                                    <Badge key={idx} variant="secondary" className="border-2 border-black">
                                                        {skill}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {selectedItem.professional_summary && (
                                        <div>
                                            <div className="text-sm font-medium text-slate-600 mb-2">Professional Summary</div>
                                            <p className="text-sm text-slate-700 leading-relaxed">
                                                {selectedItem.professional_summary}
                                            </p>
                                        </div>
                                    )}
                                </>
                            )}

                            {!isCandidateType(selectedItem) && 'position' in selectedItem && selectedItem.position && (
                                <div>
                                    <div className="text-sm font-medium text-slate-600 mb-2">Position</div>
                                    <p className="text-base text-slate-900">{selectedItem.position}</p>
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>

                <Separator className="border-t-2 border-black" />

                {/* Action Buttons */}
                <div className="p-4 bg-slate-50 flex gap-3 justify-end border-t-2 border-black">
                    <Button
                        variant="outline"
                        onClick={handleReject}
                        disabled={isLoading}
                        className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-red-600 hover:bg-red-50"
                    >
                        <XCircle className="h-4 w4 mr-2" />
                        Reject
                    </Button>
                    <Button
                        onClick={handleApprove}
                        disabled={isLoading || !firstName}
                        className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] bg-green-600 hover:bg-green-700"
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Processing...
                            </>
                        ) : (
                            <>
                                <CheckCircle2 className="h-4 w-4 mr-2" />
                                {isEditing ? 'Save & Approve' : 'Approve'}
                            </>
                        )}
                    </Button>
                </div>
            </Card>
        </div>
    );
}
