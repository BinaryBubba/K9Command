# K9Command - PRD

## Original Problem Statement
K9Command is evolving from a dog boarding/daycare platform into a general-purpose staff operations platform (Connecteam-class), customized for kennel operations but not limited to them.

## Tech Stack
- **Frontend:** React 18, Tailwind CSS, Shadcn/UI, Zustand
- **Backend:** FastAPI with Pydantic, MongoDB (Motor async)
- **Auth:** JWT multi-role (Customer, Staff, Admin)
- **Payments:** Square SDK (MOCKED)

---

## CONNECTEAM PARITY - PHASE 1 ✅ COMPLETE (Data Models & Rules)

### GPS Time Clock & Attendance
- ✅ GPS clock in/out with coordinate capture
- ✅ Geofencing with configurable zones (100m default)
- ✅ Break tracking (start/end with GPS)
- ✅ Punch rounding rules (5/10/15 min intervals)
- ✅ Discrepancy detection (missing punches, geofence violations)

**Endpoints:**
```
POST /api/timeclock/clock-in - Clock in with GPS
POST /api/timeclock/clock-out - Clock out with GPS
GET  /api/timeclock/entries - List time entries
GET  /api/timeclock/entries/current - Current active entry

POST /api/timeclock/geofences - Create geofence (admin)
GET  /api/timeclock/geofences - List geofences

POST /api/timeclock/breaks/start - Start break
POST /api/timeclock/breaks/end - End break
GET  /api/timeclock/breaks - List breaks

POST /api/timeclock/break-policies - Create policy (admin)
GET  /api/timeclock/break-policies - List policies

POST /api/timeclock/overtime-rules - Create OT rule (admin)
GET  /api/timeclock/overtime-rules - List OT rules
PATCH /api/timeclock/overtime-rules/{id} - Update rule

POST /api/timeclock/rounding-rules - Create rounding rule (admin)
GET  /api/timeclock/rounding-rules - List rules
```

### Pay Periods & Timesheets
- ✅ Pay period management (weekly, biweekly, semimonthly, monthly)
- ✅ Timesheet approval workflow
- ✅ Pay period locking

**Endpoints:**
```
POST /api/timeclock/pay-periods - Create period (admin)
GET  /api/timeclock/pay-periods - List periods
POST /api/timeclock/pay-periods/{id}/approve - Approve entries
POST /api/timeclock/pay-periods/{id}/lock - Lock period
GET  /api/timeclock/pay-periods/{id}/summary - Timesheet summary
```

### Forms Engine
- ✅ Form templates with field types: text, number, date, select, checkbox, photo, signature, GPS, barcode
- ✅ Conditional field logic
- ✅ Form submissions with signature capture
- ✅ GPS location stamping on submissions
- ✅ Draft/submit/review workflow
- ✅ Task templates with checklists

**Endpoints:**
```
POST /api/forms/templates - Create template (admin)
GET  /api/forms/templates - List templates
GET  /api/forms/templates/{id} - Get template
PATCH /api/forms/templates/{id} - Update template
DELETE /api/forms/templates/{id} - Deactivate template

POST /api/forms/submissions - Submit form
GET  /api/forms/submissions - List submissions
GET  /api/forms/submissions/{id} - Get submission
PATCH /api/forms/submissions/{id} - Update/submit draft
POST /api/forms/submissions/{id}/review - Approve/reject

POST /api/forms/task-templates - Create task template (admin)
GET  /api/forms/task-templates - List task templates
POST /api/forms/task-templates/{id}/create-task - Create task from template

GET  /api/forms/analytics/submissions - Submission analytics
GET  /api/forms/analytics/tasks - Task completion analytics
```

### HR / Time Off
- ✅ Time off policies (vacation, sick, personal, etc.)
- ✅ Accrual rules (per pay period, monthly, yearly, anniversary)
- ✅ Balance tracking and carryover
- ✅ Time off request workflow with approval
- ✅ Auto-approve option for short requests
- ✅ Advance notice enforcement

**Endpoints:**
```
POST /api/hr/time-off-policies - Create policy (admin)
GET  /api/hr/time-off-policies - List policies
PATCH /api/hr/time-off-policies/{id} - Update policy
DELETE /api/hr/time-off-policies/{id} - Deactivate policy

POST /api/hr/time-off-requests - Submit request
GET  /api/hr/time-off-requests - List requests
POST /api/hr/time-off-requests/{id}/review - Approve/reject
POST /api/hr/time-off-requests/{id}/cancel - Cancel request

GET  /api/hr/balances - Get my balances
GET  /api/hr/balances/{staff_id} - Get staff balances (admin)
POST /api/hr/balances/{staff_id}/adjust - Manual adjustment (admin)
POST /api/hr/balances/run-accrual - Run accrual job (admin)

GET  /api/hr/reports/time-off-summary - Time off report
```

### Communications
- ✅ Announcements with targeting (role/team/staff)
- ✅ Required acknowledgements
- ✅ Priority levels (low/normal/high/urgent)
- ✅ Pinned announcements
- ✅ Scheduled publishing

**Endpoints:**
```
POST /api/comms/announcements - Create announcement (admin)
GET  /api/comms/announcements - List announcements
GET  /api/comms/announcements/{id} - Get announcement
PATCH /api/comms/announcements/{id} - Update announcement
DELETE /api/comms/announcements/{id} - Archive announcement

POST /api/comms/announcements/{id}/acknowledge - Acknowledge
GET  /api/comms/announcements/{id}/acknowledgements - List acks (admin)
GET  /api/comms/announcements/pending-acknowledgements - Pending for user
```

### Training & Knowledge Base
- ✅ Training courses with sections
- ✅ Course progress tracking
- ✅ Quiz system with scoring
- ✅ Knowledge base with search, tags, versioning

**Endpoints:**
```
POST /api/comms/courses - Create course (admin)
GET  /api/comms/courses - List courses
GET  /api/comms/courses/{id} - Get course
PATCH /api/comms/courses/{id} - Update course

GET  /api/comms/courses/{id}/progress - Get my progress
POST /api/comms/courses/{id}/start - Start course
POST /api/comms/courses/{id}/complete-section - Complete section

POST /api/comms/quizzes - Create quiz (admin)
GET  /api/comms/quizzes/{id} - Get quiz
POST /api/comms/quizzes/{id}/submit - Submit quiz answers

POST /api/comms/knowledge - Create article (admin)
GET  /api/comms/knowledge - List/search articles
GET  /api/comms/knowledge/{id} - Get article
PATCH /api/comms/knowledge/{id} - Update article
GET  /api/comms/knowledge/categories/list - List categories
```

---

## CONNECTEAM PARITY - PHASE 2 ✅ COMPLETE (Time Clock & Scheduling)

### Backend (Completed)
- ✅ Kiosk mode for shared device clock in/out
- ✅ Shift templates and repeating shifts
- ✅ Shift swap/trade request workflow
- ✅ Planned vs actual hours reporting
- ✅ Discrepancy tracking and reporting

### Frontend (Completed)
- ✅ Staff time clock interface with GPS capture (`/staff/time-clock`)
- ✅ Schedule view with weekly calendar (`/staff/schedule`)
- ✅ Kiosk mode with PIN entry pad (`/kiosk`)
- ✅ Admin timesheet management dashboard (`/admin/time-management`)
- ✅ Pay period approval workflow UI
- ✅ Staff/Admin dashboard navigation updates

**Routes:**
```
/staff/time-clock - GPS clock in/out, break tracking, elapsed timer
/staff/schedule - Weekly calendar, shift view, swap requests
/kiosk?device=CODE - Shared device PIN-based clock in/out
/admin/time-management - Pay periods, timesheet summary, approve/lock
/admin/schedule - Admin view of all staff schedules
```

---

## CONNECTEAM PARITY - PHASE 3 ✅ COMPLETE (Tasks, Forms, HR)

### Backend (Completed - Previous Session)
- ✅ Form templates API with all field types
- ✅ Form submissions with signature & GPS capture
- ✅ Task templates and task creation
- ✅ Time off policies and requests
- ✅ Approval workflow

### Frontend (Completed)
- ✅ **Form Builder** (`/admin/forms/builder`) - Drag-drop field palette, 16+ field types, preview, settings
- ✅ **Forms Management** (`/admin/forms`) - Template list, submissions table, analytics
- ✅ **Staff Forms** (`/staff/forms`) - Available forms, drafts, submitted tabs
- ✅ **Form Submission** (`/staff/forms/submit/:id`) - All field types, signature canvas, GPS/photo capture
- ✅ **Task Dashboard** (`/staff/tasks`, `/admin/tasks`) - Task list, create modal, filters, status management
- ✅ **Time Off** (`/staff/time-off`, `/admin/time-off`) - Balance cards, request form, calendar view, approval workflow

**Field Types Supported:**
- Basic: text, textarea, number, date, time, datetime
- Choice: select, multiselect, checkbox, radio
- Media: file, photo, signature, GPS, barcode
- Layout: section, instructions

---

## CONNECTEAM PARITY - PHASE 4 (Communication & Reporting)

### Pending Implementation
- [ ] Announcements feed UI
- [ ] Training course viewer
- [ ] Quiz taking interface
- [ ] Knowledge base search and viewer
- [ ] CSV/PDF export for timesheets, schedules, time off

---

## CONNECTEAM PARITY - PHASE 5 (Automation API)

### Pending Implementation
- [ ] Event model and trigger registry
- [ ] Rule engine for automation
- [ ] Webhook configuration
- [ ] Integration API for payroll systems
- [ ] Audit logs and job status endpoints

---

## K9COMMAND ORIGINAL FEATURES

### Phase 1 - Data & Rules ✅ COMPLETE
- Service types, add-ons, dynamic pricing
- Capacity rules, cancellation policies
- System settings, invoices, payments

### Phase 2 - Staff Ops ✅ COMPLETE (Backend)
- Ops dashboard, approval queue
- Staff assignments, play groups
- Feeding schedules

### Phase 3 - Customer UX ✅ COMPLETE (Backend)
- Enhanced booking v2
- Booking modification/cancellation
- Payment history, invoices

### Phase 4 - Automation ✅ COMPLETE (Backend)
- Notifications, templates
- Automation rules
- Event logging

### Known Issues (Pending)
- Customer booking flow - needs frontend verification
- Staff booking creation - needs frontend verification

---

## Test Accounts
- Customer: `customer_test@k9.com` / `Test123!`
- Staff: `staff_test@k9.com` / `Test123!`
- Admin: `admin_test@k9.com` / `Test123!`

## Testing
- **Phase 1 K9Command:** `/app/test_reports/iteration_4.json` - 47/47 passed
- **Phase 1 Connecteam:** `/app/test_reports/iteration_5.json` - 53/53 passed
- **Test Files:** `/app/backend/tests/test_connecteam_phase1.py`

---

## MOCKED INTEGRATIONS
- Square Payments (mock payment IDs)
- Email Notifications (logged only)
- SMS Notifications (logged only)

---

## Architecture

### Backend Structure
```
/app/backend/
├── server.py           # Main API endpoints (K9Command original)
├── models.py           # All data models
├── routers/
│   ├── timeclock.py    # GPS clock, breaks, pay periods
│   ├── forms.py        # Forms engine, task templates
│   ├── hr.py           # Time off policies, requests, balances
│   └── communications.py # Announcements, training, knowledge
├── pricing_engine.py
├── payment_service.py
├── automation_service.py
└── auth.py
```

### Database Collections (New)
- `geofence_zones`
- `enhanced_time_entries`
- `gps_records`
- `break_entries`
- `break_policies`
- `overtime_rules`
- `punch_rounding_rules`
- `pay_periods`
- `form_templates`
- `form_submissions`
- `task_templates`
- `enhanced_tasks`
- `time_off_policies`
- `time_off_requests`
- `time_off_balances`
- `announcements`
- `acknowledgements`
- `courses`
- `course_progress`
- `quizzes`
- `quiz_attempts`
- `knowledge_articles`
