# K9Command - PRD

## Original Problem Statement
K9Command is a facility-centric pet services platform that must fully support:
- Boarding (primary)
- Daycare (primary)
- Training (light support)

It is not a marketplace. It serves one business with staff, not independent providers.
Single location first, multi-location capable by design.

**Note:** Grooming has been simplified to just "Bath before pickup" add-on.

## Tech Stack
- **Frontend:** React 18, Tailwind CSS, Shadcn/UI, Zustand
- **Backend:** FastAPI with Pydantic, MongoDB (Motor async)
- **Auth:** JWT multi-role (Customer, Staff, Admin)
- **Payments:** Square SDK (card-on-file vaulting planned)

---

## MOEGO PARITY - PHASE 1 ✅ COMPLETE (Core Data Models & Rules)

### Kennel/Run Management
- ✅ Kennel types (run, suite, crate, luxury)
- ✅ Size categories and weight restrictions
- ✅ Features (outdoor_access, webcam, climate_control, raised_bed)
- ✅ Price modifiers per kennel
- ✅ Status tracking (available, occupied, reserved, cleaning, maintenance)
- ✅ Assignment at booking time

**Endpoints:**
```
GET  /api/moego/kennels - List all kennels
POST /api/moego/kennels - Create kennel (admin)
PATCH /api/moego/kennels/{id} - Update kennel
DELETE /api/moego/kennels/{id} - Deactivate kennel
GET  /api/moego/kennels/availability/{location_id} - Check availability
```

### Time Slots
- ✅ Configurable check-in/check-out slots
- ✅ Per-slot capacity limits
- ✅ Day-of-week restrictions
- ✅ Seasonal slot overrides

**Endpoints:**
```
GET  /api/moego/slots - List time slots
POST /api/moego/slots - Create slot (admin)
PATCH /api/moego/slots/{id} - Update slot
GET  /api/moego/slots/availability/{location_id} - Slot availability for date
```

### Coupon Codes
- ✅ Percentage and flat amount discounts
- ✅ Free night (buy X get 1 free)
- ✅ Usage limits (total and per-customer)
- ✅ Min order amount / min nights requirements
- ✅ First booking only restriction
- ✅ Validity date ranges

**Endpoints:**
```
GET  /api/moego/coupons - List coupons (admin)
POST /api/moego/coupons - Create coupon (admin)
PATCH /api/moego/coupons/{id} - Update coupon
DELETE /api/moego/coupons/{id} - Deactivate coupon
POST /api/moego/coupons/validate - Validate & calculate discount
```

### Eligibility Rules
- ✅ Vaccination requirements with expiry buffer
- ✅ Weight restrictions
- ✅ Breed restrictions (allowed/blocked)
- ✅ Age restrictions
- ✅ Behavior checks (dog-friendly, aggression history)
- ✅ Hard block vs soft warning enforcement

**Endpoints:**
```
GET  /api/moego/eligibility-rules - List rules
POST /api/moego/eligibility-rules - Create rule (admin)
POST /api/moego/eligibility/check - Check dog eligibility
```

### Waitlist
- ✅ Waitlist for full dates
- ✅ Position tracking
- ✅ Offer/accept/decline workflow
- ✅ Flexible date preferences

**Endpoints:**
```
GET  /api/moego/waitlist - List waitlist entries
POST /api/moego/waitlist - Join waitlist
POST /api/moego/waitlist/{id}/offer - Offer spot (admin)
POST /api/moego/waitlist/{id}/respond - Accept/decline offer
```

### Daily Operations
- ✅ Dogs on site view
- ✅ Operations summary (occupancy, check-ins, check-outs, baths)
- ✅ Date-based filtering

**Endpoints:**
```
GET  /api/moego/operations/dogs-on-site - List dogs currently on site
GET  /api/moego/operations/summary - Daily operations summary
```

### Frontend Pages (Phase 1)
- ✅ `/admin/kennels` - Kennel Management (CRUD, grouped by type)
- ✅ `/admin/daily-ops` - Daily Operations dashboard
- ✅ `/admin/coupons` - Coupon Code management

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

## MOEGO PARITY - PHASE 2 (Booking + Ops Views) ✅ COMPLETE

### Implemented (Dec 2025)
- [x] Smart booking API with eligibility checks and auto-block logic
- [x] Smart booking UI integrated into BookStayPage with:
  - Bath Before Pickup add-on ($25/dog) with day selection (checkout/day before)
  - Coupon code input (validated at checkout)
  - Auto-block display when eligibility fails (Step 4 confirmation)
  - Eligibility warnings and errors shown to customer
- [x] Lodging map view (visual kennel grid) - `/admin/lodging-map`
  - Simple grid layout grouped by kennel type
  - Color-coded status (green=available, red=occupied)
  - Occupancy stats and filtering
- [x] Check-in/check-out workflows - `/admin/check-in-out`
  - Tabs for Check-ins, Check-outs, Baths Due
  - Item checklist for arrivals/departures
  - Payment collection on checkout
- [x] Booking approval page - `/admin/booking-approvals`
  - Review auto-blocked bookings
  - Approve with kennel assignment or reject with reason
- [x] Bath scheduling (day of/day before checkout)
- [x] In-App Notification System:
  - NotificationBell component in dashboard headers
  - Customer notified when booking auto-blocked, approved, or rejected
  - Admin notified when new booking requires approval
  - Framework for future email/SMS (MOCKED - not yet integrated)
- [x] Backend APIs:
  - POST /api/moego/bookings/smart - Smart booking with eligibility
  - GET /api/moego/operations/check-ins - Today's check-ins
  - GET /api/moego/operations/check-outs - Today's check-outs  
  - GET /api/moego/operations/baths-due - Baths due today
  - POST /api/moego/operations/check-in/{id} - Perform check-in
  - POST /api/moego/operations/check-out/{id} - Perform check-out
  - POST /api/moego/operations/bath/{id} - Mark bath complete
  - GET /api/moego/bookings/pending-approval - Pending approvals
  - POST /api/moego/bookings/{id}/approve - Approve booking
  - POST /api/moego/bookings/{id}/reject - Reject booking
  - GET /api/moego/notifications - User notifications
  - GET /api/moego/notifications/unread-count - Unread count
  - POST /api/moego/notifications/{id}/read - Mark as read
  - POST /api/moego/notifications/mark-all-read - Mark all read

### Pending
- [ ] Waitlist management UI
- [ ] Email notification integration (SendGrid/Resend - framework built)
- [ ] SMS notification integration (Twilio - framework built)

### Push Notifications ✅ COMPLETE (Dec 2025)
- [x] Web Push API (browser-native) implementation
- [x] Firebase Cloud Messaging framework (requires Firebase credentials)
- [x] Service worker (sw.js) for handling push events
- [x] PushNotificationSettings component integrated in Customer Dashboard
- [x] usePushNotifications React hook for subscription management
- [x] Backend APIs:
  - GET /api/moego/push/vapid-key - Get VAPID public key
  - POST /api/moego/push/subscribe/web - Subscribe to Web Push
  - POST /api/moego/push/subscribe/fcm - Subscribe to FCM
  - GET /api/moego/push/subscriptions - Get user subscriptions
  - DELETE /api/moego/push/unsubscribe/{id} - Unsubscribe
  - POST /api/moego/push/test - Send test notification
- [x] Push notifications sent for:
  - Booking confirmed
  - Booking pending approval (auto-blocked)
  - Booking approved
  - Booking rejected
  - Admin alerts for pending approvals

---

## MOEGO PARITY - PHASE 3 (Payments & Portal) ✅ COMPLETE

### Implemented (Dec 2025)
- [x] Square card-on-file (vaulting) - save/retrieve/delete customer cards
- [x] Deposit/pre-authorization holds with delayed capture
- [x] Direct payments with immediate capture
- [x] Refund processing (full and partial)
- [x] Customer Portal (`/customer/portal`):
  - Upcoming bookings with status and kennel info
  - Service history with one-click rebooking
  - Saved payment methods management
  - Invoice/receipt listing
- [x] Backend APIs:
  - GET /api/moego/payments/config - Payment configuration
  - POST /api/moego/payments/cards - Save card on file
  - GET /api/moego/payments/cards - Get saved cards
  - DELETE /api/moego/payments/cards/{id} - Delete card
  - POST /api/moego/payments/deposit-hold - Create pre-auth hold
  - POST /api/moego/payments/capture/{id} - Capture hold
  - POST /api/moego/payments/cancel/{id} - Cancel hold
  - POST /api/moego/payments/charge - Direct payment
  - POST /api/moego/payments/refund - Process refund
  - GET /api/moego/portal/upcoming - Upcoming bookings
  - GET /api/moego/portal/service-history - Past bookings
  - GET /api/moego/portal/invoices - Payment receipts
  - POST /api/moego/portal/rebook/{id} - One-click rebooking

### Notes
- **MOCK MODE**: Square API runs in mock mode when SQUARE_ACCESS_TOKEN is not configured
- For production: Set SQUARE_ACCESS_TOKEN, SQUARE_APPLICATION_ID, SQUARE_LOCATION_ID in backend/.env

---

## MOEGO PARITY - PHASE 4 (POS & Growth)

### Pending Implementation
- [ ] Retail inventory catalog (SKUs)
- [ ] POS checkout (in-person)
- [ ] Lead intake pipeline
- [ ] CRM lifecycle states (new/active/lapsed)
- [ ] Retention metrics (repeat rate, LTV)

---

## MOEGO PARITY - PHASE 5 (Mobile & Integrations)

### Pending Implementation (Architectural Support)
- [ ] Mobile grooming routes (if needed later)
- [ ] Service areas (zip/polygon)
- [ ] Reserve with Google integration
- [ ] Webhook/event architecture

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
