/**
 * Profile Settings Component
 * Allows users to update their personal information and change password
 */

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { 
  User, 
  Mail, 
  Phone, 
  Lock, 
  Save, 
  Loader2, 
  CheckCircle2,
  Eye,
  EyeOff,
  Shield,
  Calendar
} from 'lucide-react';
import { usePortalAuth } from '@/contexts/PortalAuthContext';
import { updateProfile, changePassword } from '@/lib/api/settings';
import type { ProfileUpdateRequest, ChangePasswordRequest } from '@/lib/api/settings';

// Profile form schema
const profileSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  phone: z.string().max(20).optional().or(z.literal('')),
});

type ProfileFormData = z.infer<typeof profileSchema>;

// Password form schema
const passwordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one digit'),
  confirm_password: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
});

type PasswordFormData = z.infer<typeof passwordSchema>;

export function ProfileSettings() {
  const { user } = usePortalAuth();
  const queryClient = useQueryClient();
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Profile form
  const profileForm = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      phone: user?.phone || '',
    },
  });

  // Password form
  const passwordForm = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  // Update form when user changes
  useEffect(() => {
    if (user) {
      profileForm.reset({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        phone: user.phone || '',
      });
    }
  }, [user, profileForm]);

  // Profile update mutation
  const profileMutation = useMutation({
    mutationFn: (data: ProfileUpdateRequest) => updateProfile(data),
    onSuccess: (updatedUser) => {
      toast.success('Profile updated successfully');
      // Update stored user in localStorage
      const storedUser = localStorage.getItem('portal_user');
      if (storedUser) {
        const parsedUser = JSON.parse(storedUser);
        const newUser = { ...parsedUser, ...updatedUser };
        localStorage.setItem('portal_user', JSON.stringify(newUser));
      }
      queryClient.invalidateQueries({ queryKey: ['current-user'] });
      // Force page reload to update context
      window.location.reload();
    },
    onError: (error: Error) => {
      toast.error('Failed to update profile', {
        description: error.message,
      });
    },
  });

  // Password change mutation
  const passwordMutation = useMutation({
    mutationFn: (data: ChangePasswordRequest) => changePassword(data),
    onSuccess: () => {
      toast.success('Password changed successfully');
      passwordForm.reset();
    },
    onError: (error: Error) => {
      toast.error('Failed to change password', {
        description: error.message,
      });
    },
  });

  const onProfileSubmit = (data: ProfileFormData) => {
    profileMutation.mutate({
      first_name: data.first_name,
      last_name: data.last_name,
      phone: data.phone || undefined,
    });
  };

  const onPasswordSubmit = (data: PasswordFormData) => {
    passwordMutation.mutate({
      current_password: data.current_password,
      new_password: data.new_password,
    });
  };

  // Get user's primary role
  const primaryRole = user?.roles?.[0];
  const roleDisplayName = typeof primaryRole === 'string' 
    ? primaryRole 
    : primaryRole?.display_name || primaryRole?.name || 'User';

  return (
    <div className="space-y-6">
      {/* Profile Header Card */}
      <Card className="border-0 shadow-sm bg-gradient-to-r from-slate-50 to-slate-100">
        <CardContent className="pt-6">
          <div className="flex items-start gap-6">
            {/* Avatar */}
            <div className="flex-shrink-0">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-2xl font-semibold shadow-lg">
                {user?.first_name?.[0]?.toUpperCase()}{user?.last_name?.[0]?.toUpperCase()}
              </div>
            </div>
            
            {/* User Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-2xl font-bold text-slate-900">
                  {user?.first_name} {user?.last_name}
                </h2>
                <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                  {roleDisplayName}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-slate-600 mb-3">
                <Mail className="h-4 w-4" />
                <span>{user?.email}</span>
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-500">
                {user?.last_login && (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>Last login: {new Date(user.last_login).toLocaleDateString()}</span>
                  </div>
                )}
                {user?.is_active && (
                  <div className="flex items-center gap-1 text-green-600">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Active</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Personal Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-slate-600" />
            <div>
              <CardTitle>Personal Information</CardTitle>
              <CardDescription>Update your personal details</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* First Name */}
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input
                  id="first_name"
                  placeholder="Enter your first name"
                  {...profileForm.register('first_name')}
                  className={profileForm.formState.errors.first_name ? 'border-red-500' : ''}
                />
                {profileForm.formState.errors.first_name && (
                  <p className="text-sm text-red-500">
                    {profileForm.formState.errors.first_name.message}
                  </p>
                )}
              </div>

              {/* Last Name */}
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input
                  id="last_name"
                  placeholder="Enter your last name"
                  {...profileForm.register('last_name')}
                  className={profileForm.formState.errors.last_name ? 'border-red-500' : ''}
                />
                {profileForm.formState.errors.last_name && (
                  <p className="text-sm text-red-500">
                    {profileForm.formState.errors.last_name.message}
                  </p>
                )}
              </div>
            </div>

            {/* Email (Read-only) */}
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  id="email"
                  type="email"
                  value={user?.email || ''}
                  disabled
                  className="pl-10 bg-slate-50"
                />
              </div>
              <p className="text-sm text-slate-500">
                Contact your administrator to change your email address
              </p>
            </div>

            {/* Phone */}
            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  id="phone"
                  type="tel"
                  placeholder="+1 (555) 000-0000"
                  {...profileForm.register('phone')}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={profileMutation.isPending || !profileForm.formState.isDirty}
              >
                {profileMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-slate-600" />
            <div>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>Update your password to keep your account secure</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-6">
            {/* Current Password */}
            <div className="space-y-2">
              <Label htmlFor="current_password">Current Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  id="current_password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  placeholder="Enter your current password"
                  {...passwordForm.register('current_password')}
                  className={`pl-10 pr-10 ${passwordForm.formState.errors.current_password ? 'border-red-500' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {passwordForm.formState.errors.current_password && (
                <p className="text-sm text-red-500">
                  {passwordForm.formState.errors.current_password.message}
                </p>
              )}
            </div>

            <Separator />

            {/* New Password */}
            <div className="space-y-2">
              <Label htmlFor="new_password">New Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  id="new_password"
                  type={showNewPassword ? 'text' : 'password'}
                  placeholder="Enter your new password"
                  {...passwordForm.register('new_password')}
                  className={`pl-10 pr-10 ${passwordForm.formState.errors.new_password ? 'border-red-500' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {passwordForm.formState.errors.new_password && (
                <p className="text-sm text-red-500">
                  {passwordForm.formState.errors.new_password.message}
                </p>
              )}
              <Alert className="bg-slate-50 border-slate-200">
                <AlertDescription className="text-sm text-slate-600">
                  Password must be at least 8 characters and include uppercase, lowercase, and a number.
                </AlertDescription>
              </Alert>
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm New Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  id="confirm_password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm your new password"
                  {...passwordForm.register('confirm_password')}
                  className={`pl-10 pr-10 ${passwordForm.formState.errors.confirm_password ? 'border-red-500' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {passwordForm.formState.errors.confirm_password && (
                <p className="text-sm text-red-500">
                  {passwordForm.formState.errors.confirm_password.message}
                </p>
              )}
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
              <Button
                type="submit"
                variant="default"
                disabled={passwordMutation.isPending}
              >
                {passwordMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Changing Password...
                  </>
                ) : (
                  <>
                    <Lock className="mr-2 h-4 w-4" />
                    Change Password
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
