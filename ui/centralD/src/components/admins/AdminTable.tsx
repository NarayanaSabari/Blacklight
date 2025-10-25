/**
 * Admin Table Component
 */

import { format } from 'date-fns';
import { Shield, MoreVertical } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
import type { PMAdmin } from '@/types';

interface AdminTableProps {
  admins: PMAdmin[];
}

export function AdminTable({ admins }: AdminTableProps) {
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
              <TableHead>Email</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Last Modified</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {admins.map((admin) => (
              <TableRow key={admin.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    {admin.email}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {format(new Date(admin.created_at), 'MMM dd, yyyy')}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {format(new Date(admin.updated_at), 'MMM dd, yyyy')}
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
                      <DropdownMenuItem>Edit Admin</DropdownMenuItem>
                      <DropdownMenuItem>Change Password</DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-destructive">
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
  );
}
