/**
 * Kanban Board Page
 * Modern visual pipeline view of candidates across different stages
 * Features: Drag-and-drop, filters (recruiter, date range, source), contact info
 */

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Search,
  User,
  MapPin,
  Briefcase,
  Clock,
  MoreHorizontal,
  Eye,
  XCircle,
  RefreshCw,
  Mail,
  Phone,
  CalendarIcon,
  GripVertical,
  X,
  Users,
  Filter,
  ChevronDown,
  Inbox,
  FileSearch,
  CheckCircle2,
  MessageSquare,
  FileText,
  PartyPopper,
} from 'lucide-react';
import { candidateApi } from '@/lib/candidateApi';
import { teamApi } from '@/lib/teamApi';
import { format, formatDistanceToNow, isAfter, isBefore, startOfDay, endOfDay } from 'date-fns';
import type { CandidateListItem, CandidateStatus } from '@/types/candidate';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { DateRange } from 'react-day-picker';

// Pipeline stage configuration with modern design
interface PipelineStage {
  id: CandidateStatus;
  label: string;
  icon: React.ElementType;
  gradient: string;
  lightBg: string;
  iconColor: string;
  borderColor: string;
  badgeBg: string;
  badgeText: string;
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 'new',
    label: 'New',
    icon: Inbox,
    gradient: 'from-blue-500 to-blue-600',
    lightBg: 'bg-blue-50',
    iconColor: 'text-blue-600',
    borderColor: 'border-blue-200',
    badgeBg: 'bg-blue-100',
    badgeText: 'text-blue-700',
  },
  {
    id: 'screening',
    label: 'Screening',
    icon: FileSearch,
    gradient: 'from-purple-500 to-purple-600',
    lightBg: 'bg-purple-50',
    iconColor: 'text-purple-600',
    borderColor: 'border-purple-200',
    badgeBg: 'bg-purple-100',
    badgeText: 'text-purple-700',
  },
  {
    id: 'ready_for_assignment',
    label: 'Ready',
    icon: CheckCircle2,
    gradient: 'from-green-500 to-green-600',
    lightBg: 'bg-green-50',
    iconColor: 'text-green-600',
    borderColor: 'border-green-200',
    badgeBg: 'bg-green-100',
    badgeText: 'text-green-700',
  },
  {
    id: 'interviewed',
    label: 'Interview',
    icon: MessageSquare,
    gradient: 'from-orange-500 to-orange-600',
    lightBg: 'bg-orange-50',
    iconColor: 'text-orange-600',
    borderColor: 'border-orange-200',
    badgeBg: 'bg-orange-100',
    badgeText: 'text-orange-700',
  },
  {
    id: 'offered',
    label: 'Offered',
    icon: FileText,
    gradient: 'from-amber-500 to-amber-600',
    lightBg: 'bg-amber-50',
    iconColor: 'text-amber-600',
    borderColor: 'border-amber-200',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-700',
  },
  {
    id: 'hired',
    label: 'Hired',
    icon: PartyPopper,
    gradient: 'from-emerald-500 to-emerald-600',
    lightBg: 'bg-emerald-50',
    iconColor: 'text-emerald-600',
    borderColor: 'border-emerald-200',
    badgeBg: 'bg-emerald-100',
    badgeText: 'text-emerald-700',
  },
];

// Helper to get status for a candidate (mapping some to visible stages)
function getVisibleStatus(status: CandidateStatus): CandidateStatus | null {
  if (status === 'processing' || status === 'pending_review') return 'new';
  if (status === 'onboarded') return 'ready_for_assignment';
  if (status === 'rejected' || status === 'withdrawn') return null;
  return status;
}

// ============================================================================
// Draggable Candidate Card
// ============================================================================

interface DraggableCandidateCardProps {
  candidate: CandidateListItem;
  onView: (id: number) => void;
  onMoveToStage: (id: number, stage: CandidateStatus) => void;
}

function DraggableCandidateCard({ candidate, onView, onMoveToStage }: DraggableCandidateCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: candidate.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(isDragging && 'opacity-50')}
    >
      <CandidateCard
        candidate={candidate}
        onView={onView}
        onMoveToStage={onMoveToStage}
        dragHandleProps={{ ...attributes, ...listeners }}
      />
    </div>
  );
}

// ============================================================================
// Candidate Card Component
// ============================================================================

interface CandidateCardProps {
  candidate: CandidateListItem;
  onView: (id: number) => void;
  onMoveToStage: (id: number, stage: CandidateStatus) => void;
  dragHandleProps?: Record<string, unknown>;
  isOverlay?: boolean;
}

function CandidateCard({ candidate, onView, onMoveToStage, dragHandleProps, isOverlay }: CandidateCardProps) {
  const initials = `${candidate.first_name?.[0] || ''}${candidate.last_name?.[0] || ''}`.toUpperCase();
  const fullName = `${candidate.first_name} ${candidate.last_name}`.trim();
  const timeAgo = candidate.created_at 
    ? formatDistanceToNow(new Date(candidate.created_at), { addSuffix: true })
    : 'Unknown';

  return (
    <Card 
      className={cn(
        "cursor-pointer bg-white border-slate-200/80 hover:border-slate-300 hover:shadow-lg transition-all duration-200 group",
        isOverlay && "shadow-2xl rotate-2 scale-105 border-primary"
      )}
      onClick={() => onView(candidate.id)}
    >
      <CardContent className="p-4">
        {/* Header with avatar, drag handle, and actions */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            {/* Drag handle */}
            {dragHandleProps && (
              <div
                {...dragHandleProps}
                className="cursor-grab active:cursor-grabbing p-1 -ml-1 rounded-md hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => e.stopPropagation()}
              >
                <GripVertical className="h-4 w-4 text-slate-400" />
              </div>
            )}
            
            <Avatar className="h-10 w-10 flex-shrink-0 border-2 border-white shadow-sm">
              <AvatarFallback className="bg-gradient-to-br from-slate-700 to-slate-900 text-white text-sm font-medium">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <h4 className="font-semibold text-slate-900 truncate text-sm">{fullName}</h4>
              {candidate.current_title && (
                <p className="text-xs text-slate-500 truncate">
                  {candidate.current_title}
                </p>
              )}
            </div>
          </div>
          
          {/* Quick actions dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48" onClick={(e) => e.stopPropagation()}>
              <DropdownMenuItem onClick={() => onView(candidate.id)}>
                <Eye className="h-4 w-4 mr-2" />
                View Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <div className="px-2 py-1.5 text-xs font-medium text-slate-500 uppercase tracking-wider">
                Move to
              </div>
              {PIPELINE_STAGES.filter(s => s.id !== candidate.status).map((stage) => {
                const Icon = stage.icon;
                return (
                  <DropdownMenuItem
                    key={stage.id}
                    onClick={() => onMoveToStage(candidate.id, stage.id)}
                    className="gap-2"
                  >
                    <Icon className={cn("h-4 w-4", stage.iconColor)} />
                    {stage.label}
                  </DropdownMenuItem>
                );
              })}
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                className="text-red-600 focus:text-red-600 gap-2"
                onClick={() => onMoveToStage(candidate.id, 'rejected')}
              >
                <XCircle className="h-4 w-4" />
                Reject
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Contact Info - Compact */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3 text-xs text-slate-500">
          {candidate.email && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <a
                    href={`mailto:${candidate.email}`}
                    className="flex items-center gap-1 hover:text-blue-600 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Mail className="h-3 w-3" />
                    <span className="truncate max-w-[100px]">{candidate.email}</span>
                  </a>
                </TooltipTrigger>
                <TooltipContent side="bottom">{candidate.email}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {candidate.phone && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <a
                    href={`tel:${candidate.phone}`}
                    className="flex items-center gap-1 hover:text-blue-600 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Phone className="h-3 w-3" />
                    <span>{candidate.phone}</span>
                  </a>
                </TooltipTrigger>
                <TooltipContent side="bottom">{candidate.phone}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Skills badges */}
        {candidate.skills && candidate.skills.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {candidate.skills.slice(0, 3).map((skill, idx) => (
              <Badge 
                key={idx} 
                variant="secondary" 
                className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 font-normal"
              >
                {skill}
              </Badge>
            ))}
            {candidate.skills.length > 3 && (
              <Badge variant="outline" className="text-[10px] px-2 py-0.5 text-slate-400 font-normal">
                +{candidate.skills.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Footer meta */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-400">
          <div className="flex items-center gap-3">
            {candidate.location && (
              <TooltipProvider delayDuration={200}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      <span className="truncate max-w-[60px]">{candidate.location}</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>{candidate.location}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            {candidate.total_experience_years !== undefined && candidate.total_experience_years > 0 && (
              <div className="flex items-center gap-1">
                <Briefcase className="h-3 w-3" />
                <span>{candidate.total_experience_years}y exp</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-1 text-slate-400">
            <Clock className="h-3 w-3" />
            <span>{timeAgo}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Droppable Kanban Column
// ============================================================================

interface KanbanColumnProps {
  stage: PipelineStage;
  candidates: CandidateListItem[];
  isLoading: boolean;
  isOver: boolean;
  onViewCandidate: (id: number) => void;
  onMoveCandidate: (id: number, stage: CandidateStatus) => void;
}

function KanbanColumn({ stage, candidates, isLoading, isOver, onViewCandidate, onMoveCandidate }: KanbanColumnProps) {
  const Icon = stage.icon;
  
  return (
    <div 
      className={cn(
        "flex flex-col w-[320px] min-w-[320px] rounded-xl transition-all duration-200",
        isOver 
          ? `${stage.lightBg} ring-2 ring-offset-2 ring-offset-slate-50 ring-${stage.iconColor.replace('text-', '')}`
          : "bg-slate-100/50"
      )}
      data-column-id={stage.id}
    >
      {/* Column header */}
      <div className={cn("px-4 py-3 rounded-t-xl", stage.lightBg)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className={cn(
              "p-1.5 rounded-lg bg-gradient-to-br shadow-sm",
              stage.gradient
            )}>
              <Icon className="h-4 w-4 text-white" />
            </div>
            <h3 className="font-semibold text-slate-800 text-sm">{stage.label}</h3>
          </div>
          <Badge 
            className={cn(
              "font-bold text-xs px-2 py-0.5 rounded-full",
              stage.badgeBg,
              stage.badgeText
            )}
          >
            {candidates.length}
          </Badge>
        </div>
      </div>

      {/* Cards container */}
      <ScrollArea className="flex-1 px-2 py-2">
        <SortableContext items={candidates.map(c => c.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2 min-h-[200px] pb-2">
            {isLoading ? (
              // Loading skeletons
              Array.from({ length: 3 }).map((_, idx) => (
                <Card key={idx} className="p-4 bg-white">
                  <div className="flex items-center gap-3 mb-3">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-28" />
                      <Skeleton className="h-3 w-36" />
                    </div>
                  </div>
                  <div className="flex gap-1 mb-3">
                    <Skeleton className="h-5 w-14 rounded-full" />
                    <Skeleton className="h-5 w-18 rounded-full" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                </Card>
              ))
            ) : candidates.length === 0 ? (
              <div className={cn(
                "flex flex-col items-center justify-center h-[200px] text-center rounded-xl border-2 border-dashed transition-all",
                isOver 
                  ? `${stage.borderColor} ${stage.lightBg}` 
                  : "border-slate-200 bg-white/50"
              )}>
                <div className={cn(
                  "p-3 rounded-full mb-3",
                  isOver ? stage.lightBg : "bg-slate-100"
                )}>
                  <User className={cn(
                    "h-6 w-6",
                    isOver ? stage.iconColor : "text-slate-400"
                  )} />
                </div>
                <p className={cn(
                  "text-sm font-medium",
                  isOver ? stage.iconColor : "text-slate-500"
                )}>
                  {isOver ? 'Drop here' : 'No candidates'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {isOver ? '' : 'Drag cards here'}
                </p>
              </div>
            ) : (
              candidates.map((candidate) => (
                <DraggableCandidateCard
                  key={candidate.id}
                  candidate={candidate}
                  onView={onViewCandidate}
                  onMoveToStage={onMoveCandidate}
                />
              ))
            )}
          </div>
        </SortableContext>
      </ScrollArea>
    </div>
  );
}

// ============================================================================
// Date Range Picker Component
// ============================================================================

interface DateRangePickerProps {
  value: DateRange | undefined;
  onChange: (range: DateRange | undefined) => void;
}

function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button 
          variant="outline" 
          size="sm" 
          className={cn(
            "h-9 w-[200px] justify-start text-left font-normal border-slate-200 bg-white",
            !value && "text-slate-500"
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4 text-slate-400" />
          {value?.from ? (
            value.to ? (
              <span className="text-slate-700">
                {format(value.from, 'MMM d')} - {format(value.to, 'MMM d')}
              </span>
            ) : (
              <span className="text-slate-700">{format(value.from, 'MMM d, yyyy')}</span>
            )
          ) : (
            <span>Date range</span>
          )}
          {value && (
            <X
              className="ml-auto h-4 w-4 text-slate-400 hover:text-slate-600"
              onClick={(e) => {
                e.stopPropagation();
                onChange(undefined);
              }}
            />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="range"
          selected={value}
          onSelect={onChange}
          numberOfMonths={2}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  );
}

// ============================================================================
// Main Kanban Board Page
// ============================================================================

export function KanbanBoardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // Filters state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [filterRecruiter, setFilterRecruiter] = useState<string>('all');
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [showFilters, setShowFilters] = useState(false);
  
  // Drag state
  const [activeId, setActiveId] = useState<number | null>(null);
  const [overColumnId, setOverColumnId] = useState<CandidateStatus | null>(null);

  // DnD Sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  );

  // Fetch all candidates
  const { data: candidatesData, isLoading, refetch } = useQuery({
    queryKey: ['candidates', 'kanban'],
    queryFn: () => candidateApi.listCandidates({ per_page: 500 }),
    staleTime: 0,
  });

  // Fetch team hierarchy for recruiter filter
  const { data: teamData } = useQuery({
    queryKey: ['team', 'hierarchy'],
    queryFn: () => teamApi.getTeamHierarchy(),
    staleTime: 5 * 60 * 1000,
  });

  const allCandidates = useMemo(() => {
    return candidatesData?.candidates || [];
  }, [candidatesData]);

  // Get unique sources for filter
  const sources = useMemo(() => {
    const sourceSet = new Set(allCandidates.map(c => c.source).filter(Boolean));
    return Array.from(sourceSet).sort();
  }, [allCandidates]);

  // Get recruiters from team hierarchy
  const recruiters = useMemo(() => {
    if (!teamData?.top_level_users) return [];
    
    const users: { id: number; name: string }[] = [];
    
    // Flatten hierarchy to get all users
    type TeamNode = { id: number; first_name: string; last_name: string; team_members?: TeamNode[] };
    const processNode = (node: TeamNode) => {
      users.push({
        id: node.id,
        name: `${node.first_name} ${node.last_name}`.trim(),
      });
      if (node.team_members) {
        node.team_members.forEach(processNode);
      }
    };
    
    (teamData.top_level_users as TeamNode[]).forEach(processNode);
    return users;
  }, [teamData]);

  // Filter and group candidates by stage
  const candidatesByStage = useMemo(() => {
    let filtered = allCandidates;

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(c => 
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(query) ||
        c.email?.toLowerCase().includes(query) ||
        c.phone?.includes(query) ||
        c.current_title?.toLowerCase().includes(query) ||
        c.skills?.some(s => s.toLowerCase().includes(query))
      );
    }

    // Apply source filter
    if (filterSource !== 'all') {
      filtered = filtered.filter(c => c.source === filterSource);
    }

    // Apply date range filter
    if (dateRange?.from) {
      const startDate = startOfDay(dateRange.from);
      const endDate = dateRange.to ? endOfDay(dateRange.to) : endOfDay(dateRange.from);
      
      filtered = filtered.filter(c => {
        if (!c.created_at) return false;
        const candidateDate = new Date(c.created_at);
        return isAfter(candidateDate, startDate) && isBefore(candidateDate, endDate);
      });
    }

    // Group by stage
    const grouped: Record<CandidateStatus, CandidateListItem[]> = {} as Record<CandidateStatus, CandidateListItem[]>;
    
    PIPELINE_STAGES.forEach(stage => {
      grouped[stage.id] = [];
    });

    filtered.forEach(candidate => {
      const visibleStatus = getVisibleStatus(candidate.status as CandidateStatus);
      if (visibleStatus && grouped[visibleStatus]) {
        grouped[visibleStatus].push(candidate);
      }
    });

    return grouped;
  }, [allCandidates, searchQuery, filterSource, dateRange]);

  // Mutation to update candidate status
  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: CandidateStatus }) => {
      return candidateApi.updateCandidate(id, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      toast.success('Candidate moved successfully');
    },
    onError: (error) => {
      console.error('Failed to update status:', error);
      toast.error('Failed to move candidate');
    },
  });

  // Get the active candidate being dragged
  const activeCandidate = useMemo(() => {
    if (!activeId) return null;
    return allCandidates.find(c => c.id === activeId) || null;
  }, [activeId, allCandidates]);

  // DnD Handlers
  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;
    if (!over) {
      setOverColumnId(null);
      return;
    }

    // Check if over a column or another card
    const overId = over.id;
    
    // Find which column this item belongs to
    for (const stage of PIPELINE_STAGES) {
      const candidatesInStage = candidatesByStage[stage.id] || [];
      if (stage.id === overId || candidatesInStage.some(c => c.id === overId)) {
        setOverColumnId(stage.id);
        return;
      }
    }
    
    setOverColumnId(null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    setOverColumnId(null);

    if (!over) return;

    const draggedCandidate = allCandidates.find(c => c.id === active.id);
    if (!draggedCandidate) return;

    // Determine target column
    let targetColumn: CandidateStatus | null = null;
    
    for (const stage of PIPELINE_STAGES) {
      const candidatesInStage = candidatesByStage[stage.id] || [];
      if (stage.id === over.id || candidatesInStage.some(c => c.id === over.id)) {
        targetColumn = stage.id;
        break;
      }
    }

    if (!targetColumn) return;

    // Check if status actually changed
    const currentVisibleStatus = getVisibleStatus(draggedCandidate.status as CandidateStatus);
    if (currentVisibleStatus === targetColumn) return;

    // Update the candidate status
    updateStatusMutation.mutate({ 
      id: draggedCandidate.id, 
      status: targetColumn 
    });
  };

  const handleViewCandidate = (id: number) => {
    navigate(`/candidates/${id}`);
  };

  const handleMoveCandidate = (id: number, stage: CandidateStatus) => {
    updateStatusMutation.mutate({ id, status: stage });
  };

  const clearFilters = () => {
    setSearchQuery('');
    setFilterSource('all');
    setFilterRecruiter('all');
    setDateRange(undefined);
  };

  const hasActiveFilters = searchQuery || filterSource !== 'all' || filterRecruiter !== 'all' || dateRange;
  const activeFilterCount = [searchQuery, filterSource !== 'all', filterRecruiter !== 'all', dateRange].filter(Boolean).length;

  // Calculate totals
  const totalInPipeline = Object.values(candidatesByStage).reduce((sum, arr) => sum + arr.length, 0);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex flex-col h-full -mt-2">
        {/* Header Bar */}
        <div className="bg-white border-b border-slate-200 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-4 mb-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            {/* Left side - Stats & Search */}
            <div className="flex items-center gap-4 flex-1 min-w-0">
              {/* Pipeline Stats */}
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
                <Users className="h-4 w-4 text-slate-500" />
                <span className="text-sm font-semibold text-slate-700">{totalInPipeline}</span>
                <span className="text-sm text-slate-500">in pipeline</span>
                {hasActiveFilters && (
                  <Badge variant="secondary" className="ml-1 text-xs">filtered</Badge>
                )}
              </div>

              {/* Search */}
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search by name, email, phone, skills..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-9 bg-slate-50 border-slate-200 focus:bg-white"
                />
                {searchQuery && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                    onClick={() => setSearchQuery('')}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </div>
            </div>

            {/* Right side - Actions */}
            <div className="flex items-center gap-2">
              {/* Filter Toggle */}
              <Button
                variant={showFilters ? "secondary" : "outline"}
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
                className="h-9 gap-2"
              >
                <Filter className="h-4 w-4" />
                Filters
                {activeFilterCount > 0 && (
                  <Badge className="ml-1 h-5 w-5 p-0 justify-center bg-blue-600">
                    {activeFilterCount}
                  </Badge>
                )}
                <ChevronDown className={cn("h-4 w-4 transition-transform", showFilters && "rotate-180")} />
              </Button>

              {/* Refresh Button */}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => refetch()}
                disabled={isLoading}
                className="h-9 gap-2"
              >
                <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
                <span className="hidden sm:inline">Refresh</span>
              </Button>
            </div>
          </div>

          {/* Collapsible Filters */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center gap-3">
              {/* Source Filter */}
              <Select value={filterSource} onValueChange={setFilterSource}>
                <SelectTrigger className="w-[160px] h-9 bg-white">
                  <SelectValue placeholder="All Sources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  {sources.map((source) => (
                    <SelectItem key={source} value={source}>
                      {source}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Recruiter Filter */}
              {recruiters.length > 0 && (
                <Select value={filterRecruiter} onValueChange={setFilterRecruiter}>
                  <SelectTrigger className="w-[180px] h-9 bg-white">
                    <SelectValue placeholder="All Recruiters" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Recruiters</SelectItem>
                    {recruiters.map((recruiter) => (
                      <SelectItem key={recruiter.id} value={recruiter.id.toString()}>
                        {recruiter.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {/* Date Range Filter */}
              <DateRangePicker value={dateRange} onChange={setDateRange} />

              {/* Clear Filters */}
              {hasActiveFilters && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={clearFilters}
                  className="h-9 text-slate-600 hover:text-slate-900"
                >
                  <X className="h-4 w-4 mr-1" />
                  Clear all
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Kanban Board */}
        <div 
          className="flex gap-4 overflow-x-auto pb-4 flex-1" 
          style={{ height: 'calc(100vh - 220px)' }}
        >
          {PIPELINE_STAGES.map((stage) => (
            <KanbanColumn
              key={stage.id}
              stage={stage}
              candidates={candidatesByStage[stage.id] || []}
              isLoading={isLoading}
              isOver={overColumnId === stage.id}
              onViewCandidate={handleViewCandidate}
              onMoveCandidate={handleMoveCandidate}
            />
          ))}
        </div>
      </div>

      {/* Drag Overlay - Shows the card being dragged */}
      <DragOverlay>
        {activeCandidate ? (
          <CandidateCard
            candidate={activeCandidate}
            onView={() => {}}
            onMoveToStage={() => {}}
            isOverlay
          />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export default KanbanBoardPage;
