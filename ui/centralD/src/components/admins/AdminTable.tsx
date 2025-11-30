/**
 * Admin Table Component
 */

import { useState } from 'react';
import { format } from 'date-fns';
import { Shield, MoreVertical, Pencil, Key, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { EditAdminDialog } from '@/components/dialogs/EditAdminDialog';
import { ChangeAdminPasswordDialog } from '@/components/dialogs/ChangeAdminPasswordDialog';
import { DeleteAdminDialog } from '@/components/dialogs/DeleteAdminDialog';
import type { PMAdmin } from '@/types';

interface AdminTableProps {
  admins: PMAdmin[];
}

export function AdminTable({ admins }: AdminTableProps) {
  const [selectedAdmin, setSelectedAdmin] = useState<PMAdmin | null>(null);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleEdit = (admin: PMAdmin) => {
    setSelectedAdmin(admin);
    setShowEditDialog(true);
  };

  const handleChangePassword = (admin: PMAdmin) => {
    setSelectedAdmin(admin);
    setShowPasswordDialog(true);
  };

  const handleDelete = (admin: PMAdmin) => {
    setSelectedAdmin(admin);
    setShowDeleteDialog(true);
  };

  if (admins.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Shield className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No administrators found</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Try adjusting your search or create a new administrator
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>All Administrators</CardTitle>
          <CardDescription>
            {admins.length} administrator{admins.length !== 1 ? 's' : ''} found
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {admins.map((admin) => (
                <TableRow key={admin.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-primary" />
                      {admin.first_name} {admin.last_name}
                    </div>
                  </TableCell>
                  <TableCell>{admin.email}</TableCell>
                  <TableCell>
                    <Badge variant={admin.is_active ? 'default' : 'secondary'}>
                      {admin.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {admin.last_login 
                      ? format(new Date(admin.last_login), 'MMM dd, yyyy HH:mm')
                      : 'Never'}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {format(new Date(admin.created_at), 'MMM dd, yyyy')}
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleEdit(admin)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Edit Admin
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleChangePassword(admin)}>
                          <Key className="mr-2 h-4 w-4" />
                          Change Password
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          className="text-destructive"
                          onClick={() => handleDelete(admin)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete Admin
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Dialogs */}
      <EditAdminDialog
        open={showEditDialog}
        onOpenChange={setShowEditDialog}
        admin={selectedAdmin}
      />
      <ChangeAdminPasswordDialog
        open={showPasswordDialog}
        onOpenChange={setShowPasswordDialog}
        admin={selectedAdmin}
      />
      <DeleteAdminDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        admin={selectedAdmin}
      />
    </>
  );
}
