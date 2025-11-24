/**
 * WorkExperienceEditor Component
 * 
 * Editor for managing work experience array.
 * Allows adding, editing, and removing work experience entries.
 */

import { useState } from 'react';
import { Plus, Trash2, ChevronDown, ChevronUp, Briefcase } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { WorkExperience } from '@/types/candidate';

interface WorkExperienceEditorProps {
    value: WorkExperience[];
    onChange: (experiences: WorkExperience[]) => void;
    disabled?: boolean;
}

const emptyExperience: WorkExperience = {
    title: '',
    company: '',
    location: '',
    start_date: '',
    end_date: '',
    is_current: false,
    description: '',
    duration_months: undefined,
};

export function WorkExperienceEditor({
    value = [],
    onChange,
    disabled = false,
}: WorkExperienceEditorProps) {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

    const addExperience = () => {
        onChange([...value, { ...emptyExperience }]);
        setExpandedIndex(value.length); // Expand the new item
    };

    const updateExperience = (index: number, field: keyof WorkExperience, fieldValue: any) => {
        const updated = value.map((exp, i) =>
            i === index ? { ...exp, [field]: fieldValue } : exp
        );
        onChange(updated);
    };

    const removeExperience = (index: number) => {
        onChange(value.filter((_, i) => i !== index));
        if (expandedIndex === index) {
            setExpandedIndex(null);
        }
    };

    const toggleExpand = (index: number) => {
        setExpandedIndex(expandedIndex === index ? null : index);
    };

    return (
        <div className="space-y-4">
            {value.map((exp, index) => (
                <Card
                    key={index}
                    className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                >
                    <CardHeader
                        className="cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors"
                        onClick={() => toggleExpand(index)}
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                <Briefcase className="h-4 w-4 text-slate-600 flex-shrink-0" />
                                <div className="min-w-0 flex-1">
                                    <CardTitle className="text-base truncate">
                                        {exp.title || 'New Position'}
                                    </CardTitle>
                                    {exp.company && (
                                        <p className="text-sm text-slate-600 truncate">{exp.company}</p>
                                    )}
                                </div>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                                {!disabled && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            removeExperience(index);
                                        }}
                                        className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                )}
                                {expandedIndex === index ? (
                                    <ChevronUp className="h-4 w-4 text-slate-600" />
                                ) : (
                                    <ChevronDown className="h-4 w-4 text-slate-600" />
                                )}
                            </div>
                        </div>
                    </CardHeader>

                    {expandedIndex === index && (
                        <CardContent className="space-y-4 pt-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <Label htmlFor={`title-${index}`}>Job Title *</Label>
                                    <Input
                                        id={`title-${index}`}
                                        value={exp.title}
                                        onChange={(e) => updateExperience(index, 'title', e.target.value)}
                                        placeholder="e.g. Senior Software Engineer"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor={`company-${index}`}>Company *</Label>
                                    <Input
                                        id={`company-${index}`}
                                        value={exp.company}
                                        onChange={(e) => updateExperience(index, 'company', e.target.value)}
                                        placeholder="e.g. Google"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor={`location-${index}`}>Location</Label>
                                    <Input
                                        id={`location-${index}`}
                                        value={exp.location || ''}
                                        onChange={(e) => updateExperience(index, 'location', e.target.value)}
                                        placeholder="e.g. San Francisco, CA"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor={`start-${index}`}>Start Date</Label>
                                    <Input
                                        id={`start-${index}`}
                                        type="month"
                                        value={exp.start_date || ''}
                                        onChange={(e) => updateExperience(index, 'start_date', e.target.value)}
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor={`end-${index}`}>End Date</Label>
                                    <Input
                                        id={`end-${index}`}
                                        type="month"
                                        value={exp.end_date || ''}
                                        onChange={(e) => updateExperience(index, 'end_date', e.target.value)}
                                        disabled={!exp.is_current && !disabled}
                                        placeholder={exp.is_current ? 'Present' : ''}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div className="flex items-center space-x-2 pt-6">
                                    <Checkbox
                                        id={`current-${index}`}
                                        checked={exp.is_current}
                                        onCheckedChange={(checked) =>
                                            updateExperience(index, 'is_current', checked)
                                        }
                                        disabled={disabled}
                                    />
                                    <Label htmlFor={`current-${index}`} className="text-sm font-normal">
                                        I currently work here
                                    </Label>
                                </div>
                            </div>

                            <div>
                                <Label htmlFor={`description-${index}`}>Description</Label>
                                <Textarea
                                    id={`description-${index}`}
                                    value={exp.description || ''}
                                    onChange={(e) => updateExperience(index, 'description', e.target.value)}
                                    placeholder="Describe your responsibilities and achievements..."
                                    rows={4}
                                    disabled={disabled}
                                    className="border-2 border-black resize-none"
                                />
                            </div>
                        </CardContent>
                    )}
                </Card>
            ))}

            {!disabled && (
                <Button
                    variant="outline"
                    onClick={addExperience}
                    className="w-full border-2 border-dashed border-primary text-primary hover:bg-primary/5"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Work Experience
                </Button>
            )}

            {value.length === 0 && disabled && (
                <p className="text-sm text-slate-500 text-center py-8">
                    No work experience added
                </p>
            )}
        </div>
    );
}
