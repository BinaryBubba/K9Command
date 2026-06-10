import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { ArrowLeftIcon, ClipboardListIcon } from 'lucide-react';

const TaskDashboardPage = () => {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-lg font-serif font-bold text-primary">Tasks</h1>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 py-12">
        <Card>
          <CardContent className="py-12 text-center space-y-3">
            <div className="bg-muted w-14 h-14 rounded-full flex items-center justify-center mx-auto">
              <ClipboardListIcon size={24} className="text-muted-foreground" />
            </div>
            <p className="font-semibold">Tasks coming soon</p>
            <p className="text-sm text-muted-foreground">
              Task management is being built in Phase 6. Check back soon.
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default TaskDashboardPage;
