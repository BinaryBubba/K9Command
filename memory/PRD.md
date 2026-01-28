# K9 Command - Kennel Operations Platform

## Original Problem Statement
Build a comprehensive "Kennel Operations 'Single Source of Truth' Platform" - a web-first application to replace existing tools like Rover and Connecteam by consolidating all business operations into one system.

## Core Requirements
1. **Customer & Dog Management**: Profiles with vaccination records, behavioral notes, medical flags
2. **Booking, Billing & Payments**: Reservation system with capacity awareness, pricing rules, Square integration (mocked)
3. **Daily Automated Updates**: Staff upload media, AI-generated daily summaries for customers
4. **Staff & Operations Management**: Employee scheduling, task checklists, time tracking, internal messaging
5. **Reviews & Reputation**: Internal feedback collection, public review encouragement
6. **Multi-Location Architecture**: Support for multiple kennel locations
7. **Security & Auditability**: Immutable logs for all critical actions

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, Zustand, react-router-dom
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB driver)
- **Database**: MongoDB
- **Authentication**: JWT-based token auth
- **Integrations**: OpenAI GPT-5.2 for AI summaries (via Emergent LLM Key), Square (mocked)

## Key Database Schema
- `users`: {email, hashed_password, full_name, role, household_id}
- `dogs`: {name, breed, owner_id, photo_url, vaccination_url, behavioral_flags}
- `bookings`: {customer_id, dog_ids, start_date, end_date, status, cost, separate_playtime_fee}
- `locations`: {name, room_capacity, crate_capacity}
- `daily_updates`: {booking_id, date, summary, status, media_items}
- `tasks`: {title, description, status, assigned_to, due_date}

---

## What's Been Implemented (December 2025)

### Authentication System ✅
- Complete auth flow for Customers, Staff, and Admins
- Registration, login, password reset with JWT tokens
- Role-based access control

### Customer Portal ✅
- Dashboard with stats (dogs, bookings)
- Add Dog page with comprehensive form
- Book a Stay page with date selection, availability check, pricing
- **P0 Bug Fixed**: Booking review page now properly displays availability and pricing

### Staff Portal ✅
- Dashboard with clock in/out, tasks, action cards
- Upload page, bookings management, approve updates pages

### Admin Portal ✅ (CRUD Controls Added)
- **AdminDashboard**: Stats overview with navigation cards
- **AdminBookingsPage**: Full CRUD - Create, Edit, Status Change, Cancel bookings
- **AdminStaffPage**: Full CRUD - Create Task, Recurring Tasks, Complete/Edit/Delete tasks
- **AdminCustomersPage**: List customers with dogs, Activate/Deactivate accounts
- **AdminReportsPage**: Basic stats (to be enhanced)
- **AdminIncidentsPage**: Incident reporting
- **AdminAuditPage**: System activity logs

### Backend APIs ✅
- All CRUD endpoints for users, dogs, bookings, tasks, locations
- Admin user management endpoints
- Task deletion endpoint
- Audit logging for all critical actions

---

## Pricing Rules
- Base: $50/night/dog
- Holiday surcharge: +20% (Dec 25, Dec 31, Jul 4, Nov 28)
- Separate playtime: +$6/day (for aggressive/unfriendly dogs)

---

## Prioritized Backlog

### P0 (Critical) - Completed ✅
- [x] Fix booking review page blank issue
- [x] Implement Admin CRUD controls for bookings, tasks, customers

### P1 (High Priority) - Upcoming
- [ ] Enhance Admin Reports & Analytics with time-based filtering (weekly/monthly)
- [ ] Add data visualization graphs to reports
- [ ] Implement Timesheet functionality (staff clock in/out viewing)

### P2 (Medium Priority)
- [ ] Build Internal Chat System (Admin-Staff, Kennel-Customer)
- [ ] Real Square payments integration (currently mocked)
- [ ] Real file storage service (AWS S3) for photo uploads

### P3 (Low Priority / Future)
- [ ] Photo watermarking and purchase feature
- [ ] Staff management features (SOP distribution, scheduling)
- [ ] Native Android/iOS applications

---

## Mocked Integrations
1. **Square Payments**: Uses mock payment ID, no real payment processing
2. **File Storage**: Uses base64 encoding instead of cloud storage
3. **AI Summaries**: Uses GPT-5.2 via Emergent LLM Key (functional)

---

## Test Credentials
- Register new users through UI at `/auth`
- Select role (customer/staff/admin) during registration
