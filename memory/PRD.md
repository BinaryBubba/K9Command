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
- Password Reset with proper token trimming and URL encoding

### Revenue Dashboard ✅
- Time-based filtering (Last 7 Days, Last 30 Days, Last Year)
- Revenue summary cards with comparison to previous period
- Revenue Trend area chart with daily/monthly data points
- Accommodation breakdown pie chart (Rooms vs Crates)
- Daily Bookings bar chart
- Average stay duration and occupancy metrics

### Customer Portal ✅
- Dashboard with stats (dogs, bookings)
- Add Dog page with comprehensive form
- Book a Stay page with date selection, availability check, pricing
- **P0 Bug Fixed**: Booking review page properly displays availability and pricing

### Staff Portal ✅
- Dashboard with clock in/out, tasks, quick action cards
- Upload page, bookings management, approve updates pages
- **NEW: Timesheet Page** - View work hours, clock in/out history, weekly totals
- **NEW: Chat Page** - Internal messaging with admins

### Admin Portal ✅ (Full CRUD Controls)
- **AdminDashboard**: Stats overview with 9 navigation cards
- **AdminBookingsPage**: Full CRUD - Create, Edit, Status Change, Cancel bookings
- **AdminStaffPage**: Full CRUD - Create Task, Recurring Tasks, Complete/Edit/Delete tasks
- **AdminCustomersPage**: List customers with dogs, Activate/Deactivate accounts
- **AdminReportsPage**: Revenue Dashboard with charts and analytics
- **AdminIncidentsPage**: Incident reporting
- **AdminAuditPage**: System activity logs
- **NEW: AdminTimesheetPage** - View all staff work hours, export to CSV, filter by staff
- **NEW: Chat Page** - Messaging with staff and customers

### Internal Chat System ✅ (NEW)
- Real-time messaging between Admin-Staff and Kennel-Customer
- Conversation list with unread counts
- Message history with timestamps
- New chat modal to start conversations with available users
- Backend APIs: GET/POST /chats, GET/POST /chats/{id}/messages

### Timesheet Functionality ✅ (NEW)
- Staff can view their own clock in/out history
- Weekly hours summary
- Current session tracking
- Admin can view all staff timesheets
- Export to CSV functionality
- Backend APIs: GET /time-entries, GET /time-entries/current

### Square Payments Integration ✅ (NEW)
- Real Square SDK integration ready
- Falls back to mock mode if API keys not configured
- Supports: Payment processing, idempotency keys, audit logging
- To enable: Add SQUARE_ACCESS_TOKEN, SQUARE_APPLICATION_ID, SQUARE_LOCATION_ID to backend/.env

---

## Pricing Rules
- Base: $50/night/dog
- Holiday surcharge: +20% (Dec 25, Dec 31, Jul 4, Nov 28)
- Separate playtime: +$6/day (for aggressive/unfriendly dogs)

---

## Prioritized Backlog

### P0 (Critical) - Completed ✅
- [x] Fix booking review page blank issue
- [x] Implement Admin CRUD controls
- [x] Revenue Dashboard with charts
- [x] Timesheet functionality
- [x] Internal Chat System
- [x] Square Payments integration (ready for keys)

### P1 (High Priority) - Future
- [ ] Enable real Square payments (user needs to add API keys)
- [ ] Real file storage service (AWS S3) for photo uploads
- [ ] AI-generated daily summaries (endpoint exists, needs testing)

### P2 (Medium Priority)
- [ ] Photo watermarking and purchase feature
- [ ] Staff management features (SOP distribution, scheduling)
- [ ] Email/SMS notifications for booking confirmations

### P3 (Low Priority / Future)
- [ ] Native Android/iOS applications
- [ ] Multi-location support UI
- [ ] Customer review system enhancement

---

## Current Integration Status
1. **Square Payments**: SDK installed, integration ready. Add keys to enable real payments:
   - `SQUARE_ACCESS_TOKEN`
   - `SQUARE_APPLICATION_ID`  
   - `SQUARE_LOCATION_ID`
2. **File Storage**: Uses base64 encoding (local storage)
3. **AI Summaries**: Uses GPT-5.2 via Emergent LLM Key (functional)

---

## Test Credentials
- Register new users through UI at `/auth`
- Select role (customer/staff/admin) during registration

## Routes
- **Customer**: /customer/dashboard, /customer/dogs/add, /customer/bookings/new, /customer/chat
- **Staff**: /staff/dashboard, /staff/upload, /staff/bookings, /staff/timesheet, /staff/chat
- **Admin**: /admin/dashboard, /admin/bookings, /admin/staff, /admin/customers, /admin/reports, /admin/incidents, /admin/audit, /admin/timesheet, /admin/chat
