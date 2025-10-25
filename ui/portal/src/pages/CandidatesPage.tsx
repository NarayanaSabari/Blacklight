/**
 * Candidates Page
 * Manage and track candidates
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Users, Plus, Search, Filter } from 'lucide-react';

export function CandidatesPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Candidates</h1>
          <p className="text-slate-600 mt-1">Manage and track your candidate pipeline</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Add Candidate
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Candidates</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>In Process</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Placed</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Candidate List</CardTitle>
              <CardDescription>View and manage all candidates</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-2">
                <Search className="h-4 w-4" />
                Search
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Users className="h-12 w-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No candidates yet</h3>
            <p className="text-slate-600 mb-4 max-w-sm">
              Start building your talent pipeline by adding candidates
            </p>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Add Your First Candidate
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
