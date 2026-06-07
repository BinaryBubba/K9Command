import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  ActivityIcon,
  HomeIcon,
  MapIcon,
  LogInIcon,
  AlertCircleIcon,
} from 'lucide-react';

const AdminOperationsHubPage = () => {
  const navigate = useNavigate();

  const tiles = [
    {
      testId: 'operations-nav-daily-ops',
      title: 'Daily Ops',
      description: 'Review daily kennel operations and task flow',
      icon: ActivityIcon,
      iconClass: 'text-orange-600',
      to: '/admin/daily-ops',
    },
    {
      testId: 'operations-nav-kennels',
      title: 'Kennel Management',
      description: 'Manage kennel occupancy and lodging operations',
      icon: HomeIcon,
      iconClass: 'text-amber-700',
      to: '/admin/kennels',
    },
    {
      testId: 'operations-nav-lodging-map',
      title: 'Lodging Map',
      description: 'View room layout and dog placement',
      icon: MapIcon,
      iconClass: 'text-blue-600',
      to: '/admin/lodging-map',
    },
    {
      testId: 'operations-nav-check-in-out',
      title: 'Check-In / Check-Out',
      description: 'Handle arrivals, departures, and front-desk flow',
      icon: LogInIcon,
      iconClass: 'text-green-600',
      to: '/admin/check-in-out',
    },
    {
      testId: 'operations-nav-incidents',
      title: 'Incidents',
      description: 'Review and manage kennel incidents',
      icon: AlertCircleIcon,
      iconClass: 'text-red-600',
      to: '/admin/incidents',
    },
  ];

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-serif font-bold text-primary">Operations</h1>
            <p className="text-sm text-muted-foreground mt-2">
              Daily kennel operations, dog flow, lodging, and front-desk workflows.
            </p>
          </div>

          <Button variant="outline" onClick={() => navigate('/admin/dashboard')}>
            Back to Admin Dashboard
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {tiles.map((tile) => {
            const Icon = tile.icon;

            return (
              <Card
                key={tile.testId}
                data-testid={tile.testId}
                className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
                onClick={() => navigate(tile.to)}
              >
                <CardContent className="p-8 text-center">
                  <Icon className={`mx-auto mb-4 ${tile.iconClass}`} size={32} />
                  <h3 className="text-lg font-semibold mb-2">{tile.title}</h3>
                  <p className="text-sm text-muted-foreground">{tile.description}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </main>
    </div>
  );
};

export default AdminOperationsHubPage;
