/**
 * EducationEditor Component
 * 
 * Editor for managing education array.
 * Allows adding, editing, and removing education entries.
 */

import { useState } from 'react';
import { Plus, Trash2, ChevronDown, ChevronUp, GraduationCap, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Education } from '@/types/candidate';

interface EducationEditorProps {
    value: Education[];
    onChange: (education: Education[]) => void;
    disabled?: boolean;
    errors?: Record<string, string>;
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
    errors = {},
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

    const getFieldError = (index: number, field: string): string | undefined => {
        const errorKey = `education.${index}.${field}`;
        return errors[errorKey] || errors[`education.${field}`] || errors['education'];
    };

    const hasFieldError = (index: number, field: string): boolean => {
        return !!getFieldError(index, field);
    };

    const hasEntryErrors = (index: number): boolean => {
        const entryFields = ['degree', 'institution', 'graduation_year', 'gpa'];
        return entryFields.some(field => hasFieldError(index, field));
    };

    return (
        <div className="space-y-4">
            {value.map((edu, index) => (
                <Card
                    key={index}
                    className={`border-2 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${hasEntryErrors(index) ? 'border-red-600' : 'border-black'}`}
                >
                    <CardHeader
                        className={`cursor-pointer hover:bg-slate-100 transition-colors ${hasEntryErrors(index) ? 'bg-red-50' : 'bg-slate-50'}`}
                        onClick={() => toggleExpand(index)}
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                <GraduationCap className={`h-4 w-4 flex-shrink-0 ${hasEntryErrors(index) ? 'text-red-600' : 'text-slate-600'}`} />
                                <div className="min-w-0 flex-1">
                                    <CardTitle className={`text-base truncate ${hasEntryErrors(index) ? 'text-red-700' : ''}`}>
                                        {edu.degree || 'New Degree'}
                                    </CardTitle>
                                    {edu.institution && (
                                        <p className="text-sm text-slate-600 truncate">{edu.institution}</p>
                                    )}
                                </div>
                                {hasEntryErrors(index) && !expandedIndex && (
                                    <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                                )}
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                                {!disabled && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        type="button"
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
                                        className={`border-2 ${hasFieldError(index, 'degree') ? 'border-red-600 bg-red-50' : 'border-black'}`}
                                    />
                                    {hasFieldError(index, 'degree') && (
                                        <p className="text-red-600 text-xs mt-1">{getFieldError(index, 'degree')}</p>
                                    )}
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
                                        className={`border-2 ${hasFieldError(index, 'institution') ? 'border-red-600 bg-red-50' : 'border-black'}`}
                                    />
                                    {hasFieldError(index, 'institution') && (
                                        <p className="text-red-600 text-xs mt-1">{getFieldError(index, 'institution')}</p>
                                    )}
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
                                        className={`border-2 ${hasFieldError(index, 'graduation_year') ? 'border-red-600 bg-red-50' : 'border-black'}`}
                                    />
                                    {hasFieldError(index, 'graduation_year') && (
                                        <p className="text-red-600 text-xs mt-1">{getFieldError(index, 'graduation_year')}</p>
                                    )}
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
                                        className={`border-2 ${hasFieldError(index, 'gpa') ? 'border-red-600 bg-red-50' : 'border-black'}`}
                                    />
                                    {hasFieldError(index, 'gpa') && (
                                        <p className="text-red-600 text-xs mt-1">{getFieldError(index, 'gpa')}</p>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    )}
                </Card>
            ))}

            {!disabled && (
                <Button
                    variant="outline"
                    type="button"
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
