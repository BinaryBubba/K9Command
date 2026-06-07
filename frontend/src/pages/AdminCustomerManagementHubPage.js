import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  UsersIcon,
  CalendarIcon,
  UserPlusIcon,
  MailIcon,
} from 'lucide-react';

const AdminCustomerManagementHubPage = () => {
  const navigate = useNavigate();

  const tiles = [
    {
      testId: 'customer-management-nav-customers',
      title: 'Customers',
      description: 'Manage customer records and linked account data',
      icon: UsersIcon,
      iconClass: 'text-primary',
      to: '/admin/customers',
    },
    {
      testId: 'customer-management-nav-bookings',
      title: 'Bookings',
      description: 'View and manage reservations and boarding stays',
      icon: CalendarIcon,
      iconClass: 'text-primary',
      to: '/admin/bookings',
    },
    {
      testId: 'customer-management-nav-crm',
      title: 'CRM',
      description: 'Track leads, follow-up activity, and customer opportunities',
      icon: UserPlusIcon,
      iconClass: 'text-emerald-700',
      to: '/admin/crm',
    },
    {
      testId: 'customer-management-nav-email-templates',
      title: 'Email Templates',
      description: 'Manage reusable customer communication templates',
      icon: MailIcon,
      iconClass: 'text-purple-600',
      to: '/admin/email-templates',
    },
  ];

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-serif font-bold text-primary">Customer Management</h1>
            <p className="text-sm text-muted-foreground mt-2">
              Customers, bookings, CRM tools, and communication workflows.
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

export default AdminCustomerManagementHubPage;
