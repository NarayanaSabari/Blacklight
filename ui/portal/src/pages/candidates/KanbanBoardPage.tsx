/**
 * Kanban Board Page
 * Visual pipeline view of candidates across different stages
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
  Filter,
  Mail,
  Phone,
  CalendarIcon,
  GripVertical,
  X,
} from 'lucide-react';
import { candidateApi } from '@/lib/candidateApi';
import { teamApi } from '@/lib/teamApi';
import { format, formatDistanceToNow, isAfter, isBefore, startOfDay, endOfDay } from 'date-fns';
import type { CandidateListItem, CandidateStatus } from '@/types/candidate';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { DateRange } from 'react-day-picker';

// Pipeline stage configuration
interface PipelineStage {
  id: CandidateStatus;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  dropBgColor: string;
  icon: string;
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 'new',
    label: 'New',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    dropBgColor: 'bg-blue-100/50',
    icon: '📥',
  },
  {
    id: 'screening',
    label: 'Screening',
    color: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    dropBgColor: 'bg-purple-100/50',
    icon: '🔍',
  },
  {
    id: 'ready_for_assignment',
    label: 'Ready',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    dropBgColor: 'bg-green-100/50',
    icon: '✅',
  },
  {
    id: 'interviewed',
    label: 'Interviewing',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    dropBgColor: 'bg-orange-100/50',
    icon: '💬',
  },
  {
    id: 'offered',
    label: 'Offered',
    color: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    dropBgColor: 'bg-amber-100/50',
    icon: '📋',
  },
  {
    id: 'hired',
    label: 'Hired',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    dropBgColor: 'bg-emerald-100/50',
    icon: '🎉',
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
        "cursor-pointer hover:shadow-md transition-all hover:border-primary/50 group",
        isOverlay && "shadow-xl rotate-2 scale-105"
      )}
      onClick={() => onView(candidate.id)}
    >
      <CardContent className="p-3">
        {/* Header with avatar, drag handle, and actions */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            {/* Drag handle */}
            {dragHandleProps && (
              <div
                {...dragHandleProps}
                className="cursor-grab active:cursor-grabbing p-1 -ml-1 rounded hover:bg-muted"
                onClick={(e) => e.stopPropagation()}
              >
                <GripVertical className="h-4 w-4 text-muted-foreground" />
              </div>
            )}
            
            <Avatar className="h-8 w-8 flex-shrink-0">
              <AvatarFallback className="bg-primary/10 text-primary text-xs">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <h4 className="font-medium text-sm truncate">{fullName}</h4>
              {candidate.current_title && (
                <p className="text-xs text-muted-foreground truncate">
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
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
              <DropdownMenuItem onClick={() => onView(candidate.id)}>
                <Eye className="h-4 w-4 mr-2" />
                View Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                Move to Stage
              </div>
              {PIPELINE_STAGES.filter(s => s.id !== candidate.status).map((stage) => (
                <DropdownMenuItem
                  key={stage.id}
                  onClick={() => onMoveToStage(candidate.id, stage.id)}
                >
                  <span className="mr-2">{stage.icon}</span>
                  {stage.label}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                className="text-destructive"
                onClick={() => onMoveToStage(candidate.id, 'rejected')}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Contact Info - Email & Phone */}
        <div className="space-y-1 mb-2">
          {candidate.email && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <a
                    href={`mailto:${candidate.email}`}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Mail className="h-3 w-3 flex-shrink-0" />
                    <span className="truncate">{candidate.email}</span>
                  </a>
                </TooltipTrigger>
                <TooltipContent>{candidate.email}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {candidate.phone && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <a
                    href={`tel:${candidate.phone}`}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Phone className="h-3 w-3 flex-shrink-0" />
                    <span className="truncate">{candidate.phone}</span>
                  </a>
                </TooltipTrigger>
                <TooltipContent>{candidate.phone}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Skills badges */}
        {candidate.skills && candidate.skills.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {candidate.skills.slice(0, 3).map((skill, idx) => (
              <Badge key={idx} variant="secondary" className="text-[10px] px-1.5 py-0">
                {skill}
              </Badge>
            ))}
            {candidate.skills.length > 3 && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                +{candidate.skills.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Meta info */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {candidate.location && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1 truncate max-w-[80px]">
                    <MapPin className="h-3 w-3 flex-shrink-0" />
                    <span className="truncate">{candidate.location}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>{candidate.location}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {candidate.total_experience_years !== undefined && candidate.total_experience_years > 0 && (
            <div className="flex items-center gap-1">
              <Briefcase className="h-3 w-3" />
              <span>{candidate.total_experience_years}y</span>
            </div>
          )}
          <div className="flex items-center gap-1 ml-auto">
            <Clock className="h-3 w-3" />
            <span className="truncate">{timeAgo}</span>
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
  return (
    <div 
      className={cn(
        "flex flex-col min-w-[300px] max-w-[340px] rounded-lg transition-colors",
        isOver ? stage.dropBgColor : "bg-muted/30"
      )}
      data-column-id={stage.id}
    >
      {/* Column header */}
      <div className={`px-3 py-2 rounded-t-lg ${stage.bgColor} border-b ${stage.borderColor}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">{stage.icon}</span>
            <h3 className={`font-semibold ${stage.color}`}>{stage.label}</h3>
          </div>
          <Badge variant="secondary" className="font-bold">
            {candidates.length}
          </Badge>
        </div>
      </div>

      {/* Cards container */}
      <ScrollArea className="flex-1 p-2">
        <SortableContext items={candidates.map(c => c.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2 min-h-[200px]">
            {isLoading ? (
              // Loading skeletons
              Array.from({ length: 3 }).map((_, idx) => (
                <Card key={idx} className="p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Skeleton className="h-8 w-8 rounded-full" />
                    <div className="flex-1">
                      <Skeleton className="h-4 w-24 mb-1" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                  </div>
                  <div className="flex gap-1 mb-2">
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                </Card>
              ))
            ) : candidates.length === 0 ? (
              <div className={cn(
                "flex flex-col items-center justify-center h-[200px] text-muted-foreground border-2 border-dashed rounded-lg",
                isOver && "border-primary bg-primary/5"
              )}>
                <User className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">{isOver ? 'Drop here' : 'No candidates'}</p>
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
        <Button variant="outline" size="sm" className="w-[240px] justify-start text-left font-normal">
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value?.from ? (
            value.to ? (
              <>
                {format(value.from, 'LLL dd')} - {format(value.to, 'LLL dd')}
              </>
            ) : (
              format(value.from, 'LLL dd, yyyy')
            )
          ) : (
            <span className="text-muted-foreground">Date range</span>
          )}
          {value && (
            <X
              className="ml-auto h-4 w-4 hover:text-destructive"
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
      <div className="space-y-4 h-full">
        {/* Action Bar */}
        <div className="flex items-center justify-between">
          <p className="text-muted-foreground">
            {totalInPipeline} candidates in pipeline
            {hasActiveFilters && ' (filtered)'}
          </p>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search name, email, phone, skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Source Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={filterSource} onValueChange={setFilterSource}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Source" />
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
          </div>

          {/* Recruiter Filter */}
          {recruiters.length > 0 && (
            <Select value={filterRecruiter} onValueChange={setFilterRecruiter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Recruiter" />
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
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>

        {/* Kanban Board */}
        <div className="flex gap-4 overflow-x-auto pb-4" style={{ height: 'calc(100vh - 300px)' }}>
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
