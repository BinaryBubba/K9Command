# K9 Command - Kennel Operations Platform

## Original Problem Statement
Build a comprehensive "Kennel Operations 'Single Source of Truth' Platform" - a web-first application to replace existing tools like Rover and Connecteam by consolidating all business operations into one system.

## Core Requirements
1. **Customer & Dog Management**: Profiles with vaccination records, behavioral notes, medical flags
2. **Booking, Billing & Payments**: Reservation system with capacity awareness, pricing rules, Square integration
3. **Daily Automated Updates**: Staff upload media, AI-generated daily summaries for customers
4. **Staff & Operations Management**: Employee scheduling, task checklists, time tracking, internal messaging
5. **Reviews & Reputation**: Internal feedback collection, public review encouragement
6. **Multi-Location Architecture**: Support for multiple kennel locations
7. **Security & Auditability**: Immutable logs for all critical actions

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, Zustand, react-router-dom, Recharts
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB driver), Square SDK
- **Database**: MongoDB
- **Authentication**: JWT-based token auth
- **Integrations**: OpenAI GPT-5.2 for AI summaries, Square Payments (ready for production keys)

---

## What's Been Implemented (January 2026)

### Authentication System ✅
- Complete auth flow for Customers, Staff, and Admins
- Registration, login, password reset with JWT tokens
- Role-based access control

### Revenue Dashboard ✅
- Time-based filtering (Last 7 Days, Last 30 Days, Last Year)
- Revenue summary cards with comparison to previous period
- Revenue Trend area chart, Accommodation pie chart, Daily Bookings bar chart

### Customer Portal ✅
- Dashboard with stats, Add Dog page, Book a Stay page
- Chat with kennel staff

### Staff Portal ✅
- **Dashboard**: Clock in/out, tasks, quick action cards
- **Bookings CRUD**: Create, edit, delete with modification reason field
- **Timesheet**: Clock in/out, request modifications to past entries, weekly totals (Mon-Sun)
- **Chat**: Separate tabs for Staff vs Customer conversations

### Admin Portal ✅ (Complete)
- **Dashboard**: Stats overview with 9 navigation cards
- **Bookings**: Full CRUD - Create, Edit, Status Change, Cancel (BUG FIXED: edit no longer returns "not found")
- **Staff Management**: Tasks with completion tracking (who completed), Shift Scheduler CRUD
- **Customer Management**: Full CRUD - Create, Edit, Delete, Activate/Deactivate
- **Incidents**: Full CRUD - Create, Edit, Delete, Resolve with notes
- **Timesheets**: Weekly totals (Mon-Sun), CRUD, Modification Request Approval, CSV Export
- **Reports**: Revenue Dashboard with charts
- **Audit Logs**: System activity tracking
- **Chat**: Tabs for Staff vs Customer conversations

### Internal Chat System ✅
- Real-time messaging: Admin ↔ Staff, Kennel ↔ Customer
- **Separate tabs**: All, Staff (internal), Customers
- Unread counts, message history, new chat modal

### Timesheet System ✅
- Staff: Clock in/out, request modifications with reason
- Admin: Approve/reject modification requests, full CRUD, weekly totals Mon-Sun

### Shift Scheduler ✅
- Create/Edit/Delete shifts for staff
- View shifts grouped by date
- Staff assignment and location tracking

---

## Test Data Available
- **Test Customer**: test_customer@example.com / TestPass123!
- **Dogs**: Buddy (Golden Retriever), Max (German Shepherd)
- **Active Booking**: Checked-in status, ready for photo upload testing

## Pricing Rules
- Base: $50/night/dog
- Holiday surcharge: +20%
- Separate playtime: +$6/day

---

## Prioritized Backlog

### P0 (Critical) - All Complete ✅
- [x] Fix booking review page
- [x] Admin CRUD controls
- [x] Revenue Dashboard
- [x] Timesheet functionality with modification requests
- [x] Internal Chat System with tabs
- [x] Square Payments integration
- [x] Shift Scheduler
- [x] Task completion tracking
- [x] Customer CRUD
- [x] Incident CRUD
- [x] Time entry CRUD + approval
- [x] Staff Bookings CRUD with reason field

### P1 (High Priority) - Future
- [ ] Enable real Square payments (add API keys)
- [ ] Real file storage (AWS S3)
- [ ] AI daily summary testing

### P2 (Medium Priority)
- [ ] Photo watermarking
- [ ] Email/SMS notifications

### P3 (Low Priority)
- [ ] Native mobile apps
- [ ] Multi-location UI

---

## Current Integration Status
1. **Square Payments**: SDK installed, mock mode (add keys to enable)
2. **File Storage**: Base64 encoding (local)
3. **AI Summaries**: GPT-5.2 via Emergent LLM Key

## Routes
- **Customer**: /customer/dashboard, /customer/dogs/add, /customer/bookings/new, /customer/chat
- **Staff**: /staff/dashboard, /staff/upload, /staff/bookings, /staff/timesheet, /staff/chat
- **Admin**: /admin/dashboard, /admin/bookings, /admin/staff, /admin/customers, /admin/reports, /admin/incidents, /admin/audit, /admin/timesheet, /admin/chat
