/**
 * EducationEditor Component
 * 
 * Editor for managing education array.
 * Allows adding, editing, and removing education entries.
 */

import { useState } from 'react';
import { Plus, Trash2, ChevronDown, ChevronUp, GraduationCap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Education } from '@/types/candidate';

interface EducationEditorProps {
    value: Education[];
    onChange: (education: Education[]) => void;
    disabled?: boolean;
}

const emptyEducation: Education = {
    degree: '',
    field_of_study: '',
    institution: '',
    graduation_year: undefined,
    gpa: undefined,
};

export function EducationEditor({
    value = [],
    onChange,
    disabled = false,
}: EducationEditorProps) {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

    const addEducation = () => {
        onChange([...value, { ...emptyEducation }]);
        setExpandedIndex(value.length); // Expand the new item
    };

    const updateEducation = (index: number, field: keyof Education, fieldValue: any) => {
        const updated = value.map((edu, i) =>
            i === index ? { ...edu, [field]: fieldValue } : edu
        );
        onChange(updated);
    };

    const removeEducation = (index: number) => {
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
            {value.map((edu, index) => (
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
                                <GraduationCap className="h-4 w-4 text-slate-600 flex-shrink-0" />
                                <div className="min-w-0 flex-1">
                                    <CardTitle className="text-base truncate">
                                        {edu.degree || 'New Degree'}
                                    </CardTitle>
                                    {edu.institution && (
                                        <p className="text-sm text-slate-600 truncate">{edu.institution}</p>
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
                                            removeEducation(index);
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
                                    <Label htmlFor={`degree-${index}`}>Degree *</Label>
                                    <Input
                                        id={`degree-${index}`}
                                        value={edu.degree}
                                        onChange={(e) => updateEducation(index, 'degree', e.target.value)}
                                        placeholder="e.g. Bachelor of Science"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor={`field-${index}`}>Field of Study</Label>
                                    <Input
                                        id={`field-${index}`}
                                        value={edu.field_of_study || ''}
                                        onChange={(e) => updateEducation(index, 'field_of_study', e.target.value)}
                                        placeholder="e.g. Computer Science"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div className="md:col-span-2">
                                    <Label htmlFor={`institution-${index}`}>Institution *</Label>
                                    <Input
                                        id={`institution-${index}`}
                                        value={edu.institution}
                                        onChange={(e) => updateEducation(index, 'institution', e.target.value)}
                                        placeholder="e.g. Massachusetts Institute of Technology"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor={`grad-year-${index}`}>Graduation Year</Label>
                                    <Input
                                        id={`grad-year-${index}`}
                                        type="number"
                                        min="1950"
                                        max="2050"
                                        value={edu.graduation_year || ''}
                                        onChange={(e) =>
                                            updateEducation(
                                                index,
                                                'graduation_year',
                                                e.target.value ? parseInt(e.target.value) : undefined
                                            )
                                        }
                                        placeholder="e.g. 2020"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>

                                <div>
                                    <Label htmlFor={`gpa-${index}`}>GPA (Optional)</Label>
                                    <Input
                                        id={`gpa-${index}`}
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        max="4.0"
                                        value={edu.gpa || ''}
                                        onChange={(e) =>
                                            updateEducation(
                                                index,
                                                'gpa',
                                                e.target.value ? parseFloat(e.target.value) : undefined
                                            )
                                        }
                                        placeholder="e.g. 3.8"
                                        disabled={disabled}
                                        className="border-2 border-black"
                                    />
                                </div>
                            </div>
                        </CardContent>
                    )}
                </Card>
            ))}

            {!disabled && (
                <Button
                    variant="outline"
                    onClick={addEducation}
                    className="w-full border-2 border-dashed border-primary text-primary hover:bg-primary/5"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Education
                </Button>
            )}

            {value.length === 0 && disabled && (
                <p className="text-sm text-slate-500 text-center py-8">
                    No education added
                </p>
            )}
        </div>
    );
}
