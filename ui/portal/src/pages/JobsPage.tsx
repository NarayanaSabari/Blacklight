/**
 * Jobs Page
 * Manage job postings and requisitions
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Briefcase, Plus, Search, Filter } from 'lucide-react';

export function JobsPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Job Postings</h1>
          <p className="text-slate-600 mt-1">Create and manage job openings</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Create Job
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Jobs</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Open</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>In Progress</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Filled</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Active Job Postings</CardTitle>
              <CardDescription>View and manage all job openings</CardDescription>
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
            <Briefcase className="h-12 w-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No job postings yet</h3>
            <p className="text-slate-600 mb-4 max-w-sm">
              Create your first job posting to start attracting talent
            </p>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Create Your First Job
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
