/**
 * Invite User Dialog Component
 * Form to create new portal users (TENANT_ADMIN only)
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { toast } from 'sonner';
import { Loader2, Mail, User, Phone, Lock, Shield, CheckCircle2 } from 'lucide-react';
import { createUser } from '@/lib/api/users';
import { fetchRoles } from '@/lib/api/roles';

interface InviteUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function InviteUserDialog({ open, onOpenChange }: InviteUserDialogProps) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    phone: '',
    role_id: 0,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Fetch roles with permissions
  const { data: rolesData, isLoading: rolesLoading } = useQuery({
    queryKey: ['roles', 'with-permissions'],
    queryFn: () => fetchRoles(true),
    enabled: open,
  });

  const createUserMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User invited successfully');
      resetForm();
      onOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to invite user');
    },
    onSettled: () => {
      setIsSubmitting(false);
    },
  });

  const resetForm = () => {
    setFormData({
      email: '',
      password: '',
      first_name: '',
      last_name: '',
      phone: '',
      role_id: 0,
    });
    setErrors({});
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email address';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    if (!formData.first_name) {
      newErrors.first_name = 'First name is required';
    }

    if (!formData.last_name) {
      newErrors.last_name = 'Last name is required';
    }

    if (!formData.role_id || formData.role_id === 0) {
      newErrors.role_id = 'Role is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    createUserMutation.mutate(formData);
  };

  const handleChange = (field: string, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  // Filter out TENANT_ADMIN role (can't create another TENANT_ADMIN)
  const availableRoles =
    rolesData?.roles.filter((role) => role.name !== 'TENANT_ADMIN') || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">Invite Team Member</DialogTitle>
          <DialogDescription>
            Create a new user account and assign role-based permissions
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Email */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <Label htmlFor="email">
                Email <span className="text-destructive">*</span>
              </Label>
            </div>
            <Input
              id="email"
              type="email"
              placeholder="user@company.com"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              className={errors.email ? 'border-destructive' : ''}
            />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email}</p>
            )}
            <p className="text-xs text-muted-foreground">
              User will log in with this email
            </p>
          </div>

          {/* First Name & Last Name */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <Label>Full Name <span className="text-destructive">*</span></Label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Input
                  id="first_name"
                  placeholder="First name"
                  value={formData.first_name}
                  onChange={(e) => handleChange('first_name', e.target.value)}
                  className={errors.first_name ? 'border-destructive' : ''}
                />
                {errors.first_name && (
                  <p className="text-xs text-destructive">{errors.first_name}</p>
                )}
              </div>

              <div className="space-y-2">
                <Input
                  id="last_name"
                  placeholder="Last name"
                  value={formData.last_name}
                  onChange={(e) => handleChange('last_name', e.target.value)}
                  className={errors.last_name ? 'border-destructive' : ''}
                />
                {errors.last_name && (
                  <p className="text-xs text-destructive">{errors.last_name}</p>
                )}
              </div>
            </div>
          </div>

          {/* Phone */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-muted-foreground" />
              <Label htmlFor="phone">Phone <span className="text-xs text-muted-foreground">(Optional)</span></Label>
            </div>
            <Input
              id="phone"
              placeholder="+1 (555) 123-4567"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
            />
          </div>

          {/* Role Selection */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <Label>
                Select Role <span className="text-destructive">*</span>
              </Label>
            </div>
            
            <RadioGroup
              value={formData.role_id ? formData.role_id.toString() : ''}
              onValueChange={(value) => handleChange('role_id', parseInt(value))}
              className="space-y-3"
            >
              {rolesLoading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-20 w-full rounded-lg border bg-muted/20 animate-pulse" />
                  ))}
                </div>
              ) : availableRoles.length === 0 ? (
                <div className="text-center py-8 text-sm text-muted-foreground">
                  No roles available
                </div>
              ) : (
                availableRoles.map((role) => (
                  <label
                    key={role.id}
                    htmlFor={`role-${role.id}`}
                    className={`flex items-start gap-4 p-4 rounded-lg border-2 cursor-pointer transition-all hover:border-primary/50 hover:bg-accent/50 ${
                      formData.role_id === role.id
                        ? 'border-primary bg-accent shadow-sm'
                        : 'border-border bg-background'
                    }`}
                  >
                    <RadioGroupItem
                      value={role.id.toString()}
                      id={`role-${role.id}`}
                      className="mt-1"
                    />
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-sm">{role.display_name}</h4>
                        <Badge variant="outline" className="text-xs">
                          {role.permissions?.length || 0} permissions
                        </Badge>
                      </div>
                      {role.description && (
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {role.description}
                        </p>
                      )}
                      {formData.role_id === role.id && (
                        <div className="flex items-center gap-1.5 text-xs text-primary font-medium">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Selected
                        </div>
                      )}
                    </div>
                  </label>
                ))
              )}
            </RadioGroup>
            
            {errors.role_id && (
              <p className="text-sm text-destructive flex items-center gap-1.5">
                {errors.role_id}
              </p>
            )}
          </div>

          <Separator />

          {/* Password */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-muted-foreground" />
              <Label htmlFor="password">
                Temporary Password <span className="text-destructive">*</span>
              </Label>
            </div>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={formData.password}
              onChange={(e) => handleChange('password', e.target.value)}
              className={errors.password ? 'border-destructive' : ''}
            />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password}</p>
            )}
            <p className="text-xs text-muted-foreground">
              User will be asked to change password on first login
            </p>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                resetForm();
                onOpenChange(false);
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="gap-2">
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isSubmitting ? 'Inviting...' : 'Send Invitation'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
