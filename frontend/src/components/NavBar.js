import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import {
  HomeIcon, DogIcon, CalendarIcon, UsersIcon, UserIcon,
  ActivityIcon, ClipboardListIcon, AlertCircleIcon,
  HomeIcon as KennelIcon, MenuIcon, XIcon, LogOutIcon,
  ShieldIcon,
} from 'lucide-react';

const NavBar = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const publicRoutes = ['/', '/auth', '/forgot-password', '/staff-request'];
  if (!user || publicRoutes.includes(location.pathname)) return null;

  const isAdmin = user.role === 'admin';
  const isStaff = user.role === 'staff';
  const isCustomer = user.role === 'customer';

  const dashboardPath = isAdmin ? '/admin/dashboard' : isStaff ? '/staff/dashboard' : '/customer/dashboard';

  const adminLinks = [
    { label: 'Dashboard', icon: <HomeIcon size={18} />, path: '/admin/dashboard' },
    { label: 'Check In/Out', icon: <ActivityIcon size={18} />, path: '/admin/check-in-out' },
    { label: 'Kennels', icon: <KennelIcon size={18} />, path: '/admin/kennels' },
    { label: 'Bookings', icon: <CalendarIcon size={18} />, path: '/admin/bookings' },
    { label: 'Customers', icon: <UsersIcon size={18} />, path: '/admin/customers' },
    { label: 'Meet & Greet', icon: <DogIcon size={18} />, path: '/admin/meet-and-greet' },
    { label: 'Playgroups', icon: <UsersIcon size={18} />, path: '/admin/playgroups' },
    { label: 'Forms', icon: <ClipboardListIcon size={18} />, path: '/admin/forms' },
    { label: 'Handoff', icon: <ClipboardListIcon size={18} />, path: '/staff/handoff' },
    { label: 'Tasks', icon: <ClipboardListIcon size={18} />, path: '/admin/tasks' },
    { label: 'Incidents', icon: <AlertCircleIcon size={18} />, path: '/admin/incidents' },
    { label: 'Staff', icon: <UsersIcon size={18} />, path: '/admin/staff' },
    { label: 'Forms', icon: <ClipboardListIcon size={18} />, path: '/forms' },
    { label: 'Settings', icon: <ShieldIcon size={18} />, path: '/admin/settings' },
  ];

  const staffLinks = [
    { label: 'Dashboard', icon: <HomeIcon size={18} />, path: '/staff/dashboard' },
    { label: 'Check In/Out', icon: <ActivityIcon size={18} />, path: '/staff/check-in-out' },
    { label: 'Kennels', icon: <KennelIcon size={18} />, path: '/admin/kennels' },
    { label: 'Bookings', icon: <CalendarIcon size={18} />, path: '/staff/bookings' },
    { label: 'Tasks', icon: <ClipboardListIcon size={18} />, path: '/staff/tasks' },
    { label: 'Daily Ops', icon: <ClipboardListIcon size={18} />, path: '/staff/daily-ops' },
    { label: 'Playgroups', icon: <UsersIcon size={18} />, path: '/admin/playgroups' },
    { label: 'Customers', icon: <UsersIcon size={18} />, path: '/admin/customers' },
    { label: 'Incidents', icon: <AlertCircleIcon size={18} />, path: '/admin/incidents' },
    { label: 'Forms', icon: <ClipboardListIcon size={18} />, path: '/forms' },
    { label: 'Handoff', icon: <ClipboardListIcon size={18} />, path: '/staff/handoff' },
  ];

  const customerLinks = [
    { label: 'My Account', icon: <HomeIcon size={18} />, path: '/customer/dashboard' },
    { label: 'My Profile', icon: <UserIcon size={18} />, path: '/customer/profile' },
    { label: 'Book a Stay', icon: <CalendarIcon size={18} />, path: '/customer/request' },
    { label: 'Book a Stay', icon: <CalendarIcon size={18} />, path: '/customer/request' },
    { label: 'Book a Stay', icon: <CalendarIcon size={18} />, path: '/customer/request' },
    { label: 'Book a Stay', icon: <CalendarIcon size={18} />, path: '/customer/request' },
    { label: 'Book a Stay', icon: <CalendarIcon size={18} />, path: '/customer/request' },
  ];

  const links = isAdmin ? adminLinks : isStaff ? staffLinks : customerLinks;

  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex flex-col fixed left-0 top-0 h-full w-52 bg-white border-r border-border/40 shadow-sm z-20">
        <div className="px-4 py-4 border-b border-border/40">
          <h1 className="text-base font-serif font-bold text-primary">K9 Command</h1>
          <p className="text-xs text-muted-foreground truncate">{user.full_name}</p>
        </div>
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {links.map(link => (
            <button
              key={link.path}
              onClick={() => navigate(link.path)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors text-left ${
                isActive(link.path)
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              {link.icon}
              {link.label}
            </button>
          ))}
        </nav>
        <div className="px-2 py-3 border-t border-border/40">
          <button
            onClick={() => { logout(); navigate('/'); }}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <LogOutIcon size={18} />
            Logout
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-14 bg-white border-b border-border/40 shadow-sm z-20 flex items-center justify-between px-4">
        <button onClick={() => navigate(dashboardPath)}>
          <h1 className="text-base font-serif font-bold text-primary">K9 Command</h1>
        </button>
        <div className="flex items-center gap-1">
          <button onClick={() => { logout(); navigate('/'); }} className="p-2 rounded-lg hover:bg-muted text-muted-foreground">
            <LogOutIcon size={18} />
          </button>
          <button onClick={() => setMobileOpen(!mobileOpen)} className="p-2 rounded-lg hover:bg-muted">
            {mobileOpen ? <XIcon size={20} /> : <MenuIcon size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-30" onClick={() => setMobileOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div className="absolute left-0 top-0 h-full w-64 bg-white shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="px-4 py-4 border-b">
              <h1 className="text-base font-serif font-bold text-primary">K9 Command</h1>
              <p className="text-xs text-muted-foreground">{user.full_name}</p>
            </div>
            <nav className="px-2 py-3 space-y-0.5">
              {links.map(link => (
                <button
                  key={link.path}
                  onClick={() => { navigate(link.path); setMobileOpen(false); }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors text-left ${
                    isActive(link.path)
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {link.icon}
                  {link.label}
                </button>
              ))}
            </nav>
            <div className="px-2 py-3 border-t">
              <button
                onClick={() => { logout(); navigate('/'); setMobileOpen(false); }}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted"
              >
                <LogOutIcon size={18} />
                Logout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Spacer for mobile top bar */}
      <div className="md:hidden h-14" />
    </>
  );
};

export default NavBar;
