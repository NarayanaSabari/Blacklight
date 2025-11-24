/**
 * TagInput Component
 * 
 * A reusable input component for managing arrays of strings (tags/chips).
 * Used for skills, certifications, languages, and preferred locations.
 */

import { useState, type KeyboardEvent } from 'react';
import { X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface TagInputProps {
    value: string[];
    onChange: (tags: string[]) => void;
    placeholder?: string;
    maxTags?: number;
    disabled?: boolean;
}

export function TagInput({
    value = [],
    onChange,
    placeholder = 'Add tag...',
    maxTags,
    disabled = false,
}: TagInputProps) {
    const [inputValue, setInputValue] = useState('');

    const addTag = (tag: string) => {
        const trimmedTag = tag.trim();

        // Validation
        if (!trimmedTag) return;
        if (value.some(t => t.toLowerCase() === trimmedTag.toLowerCase())) {
            // Duplicate - show feedback or just ignore
            return;
        }
        if (maxTags && value.length >= maxTags) {
            return;
        }

        onChange([...value, trimmedTag]);
        setInputValue('');
    };

    const removeTag = (index: number) => {
        onChange(value.filter((_, i) => i !== index));
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTag(inputValue);
        } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
            // Remove last tag on backspace if input is empty
            removeTag(value.length - 1);
        }
    };

    return (
        <div className="space-y-3">
            {/* Existing Tags */}
            {value.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {value.map((tag, index) => (
                        <Badge
                            key={index}
                            className="bg-primary text-primary-foreground border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] pl-3 pr-1 py-1 gap-1"
                        >
                            <span>{tag}</span>
                            {!disabled && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-4 w-4 p-0 hover:bg-transparent"
                                    onClick={() => removeTag(index)}
                                >
                                    <X className="h-3 w-3" />
                                </Button>
                            )}
                        </Badge>
                    ))}
                </div>
            )}

            {/* Input Field */}
            {(!maxTags || value.length < maxTags) && (
                <Input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onBlur={() => {
                        // Add tag when losing focus if there's text
                        if (inputValue.trim()) {
                            addTag(inputValue);
                        }
                    }}
                    placeholder={placeholder}
                    disabled={disabled}
                    className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                />
            )}

            {/* Helper Text */}
            <p className="text-xs text-slate-500">
                Press Enter or blur to add. {maxTags ? `(${value.length}/${maxTags})` : ''}
            </p>
        </div>
    );
}
