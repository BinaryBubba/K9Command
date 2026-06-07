import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  UsersRoundIcon,
  BarChartIcon,
  SettingsIcon,
  ShieldCheckIcon,
} from 'lucide-react';

const AdminAdministrationHubPage = () => {
  const navigate = useNavigate();

  const tiles = [
    {
      testId: 'administration-nav-staff-management',
      title: 'Staff Management',
      description: 'Manage staff records, roles, and admin access',
      icon: UsersRoundIcon,
      iconClass: 'text-indigo-600',
      to: '/admin/staff-management',
    },
    {
      testId: 'administration-nav-reports',
      title: 'Reports',
      description: 'View business reports and management insights',
      icon: BarChartIcon,
      iconClass: 'text-primary',
      to: '/admin/reports',
    },
    {
      testId: 'administration-nav-settings',
      title: 'Settings',
      description: 'Configure administrative and platform preferences',
      icon: SettingsIcon,
      iconClass: 'text-slate-700',
      to: '/admin/settings',
    },
    {
      testId: 'administration-nav-audit',
      title: 'Audit Logs',
      description: 'Review system actions and administrative trace history',
      icon: ShieldCheckIcon,
      iconClass: 'text-amber-700',
      to: '/admin/audit',
    },
  ];

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-serif font-bold text-primary">Administration</h1>
            <p className="text-sm text-muted-foreground mt-2">
              Administrative tools, reporting, system settings, and oversight.
            </p>
          </div>

          <Button variant="outline" onClick={() => navigate('/admin/dashboard')}>
            Back to Admin Dashboard
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
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

export default AdminAdministrationHubPage;
