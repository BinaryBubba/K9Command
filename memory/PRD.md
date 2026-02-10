# K9Command - PRD

## Original Problem Statement
K9Command is a single-facility, staff-operated dog boarding/daycare platform with customer self-service, internal staff operations tooling, and automation-first design. The goal is Rover-parity for a single facility.

## Tech Stack
- **Frontend:** React 18, Tailwind CSS, Shadcn/UI, Zustand
- **Backend:** FastAPI with Pydantic, MongoDB (Motor async)
- **Auth:** JWT multi-role (Customer, Staff, Admin)
- **Payments:** Square SDK (MOCKED), Crypto infrastructure (USDC - deferred)

---

## PHASE 1 - DATA & RULES FOUNDATION ✅ COMPLETE

### New Models Implemented
1. **ServiceType** - Boarding, Daycare, etc. with configurable pricing
2. **AddOn** - Extra services (Bath $40, Transport $25, Playtime $6/day, Feeding $6/day)
3. **CapacityRule** - Soft capacity enforcement with buffer
4. **PricingRule** - Weekend, holiday, seasonal, blackout rules
5. **CancellationPolicy** - Tiered refund policies (7d=100%, 3d=50%, <3d=0%)
6. **SystemSetting** - Admin-configurable settings (deposit %, tax rate)
7. **Payment** - Payment transaction records
8. **Invoice** - Booking invoices with line items

### Booking Model Updates
- `service_type_id` - Link to service type
- `add_ons[]` - Selected add-ons with quantities
- `deposit_amount`, `deposit_paid`, `deposit_paid_at`
- `balance_due`, `balance_paid`, `balance_paid_at`
- `requires_approval` - For over-capacity bookings
- `pricing_rules_applied[]` - Audit trail

### New Endpoints
```
GET  /api/service-types
POST /api/admin/service-types
PATCH/DELETE /api/admin/service-types/{id}

GET  /api/add-ons
POST /api/admin/add-ons
PATCH/DELETE /api/admin/add-ons/{id}

GET  /api/admin/capacity-rules
POST /api/admin/capacity-rules
PATCH/DELETE /api/admin/capacity-rules/{id}

GET  /api/admin/pricing-rules
POST /api/admin/pricing-rules
PATCH/DELETE /api/admin/pricing-rules/{id}

GET  /api/cancellation-policies
POST /api/admin/cancellation-policies
PATCH/DELETE /api/admin/cancellation-policies/{id}

GET  /api/admin/settings
PATCH /api/admin/settings/{key}

POST /api/pricing/calculate - Server-side price engine

GET  /api/payments/providers
POST /api/payments/deposit
POST /api/payments/balance
GET  /api/payments/history

POST /api/bookings/{id}/cancel - Policy-aware cancellation

GET  /api/invoices
GET  /api/invoices/{id}
```

---

## PHASE 2 - STAFF OPERATIONS ✅ COMPLETE (Backend)

### Features Implemented
1. ✅ Daily capacity dashboard (`GET /api/ops/dashboard`)
2. ✅ Upcoming arrivals/departures view (included in dashboard)
3. ✅ Booking approval queue (`GET /api/ops/approval-queue`)
4. ✅ Approve/Reject bookings (`POST /api/ops/bookings/{id}/approve|reject`)
5. ✅ Dog ↔ Staff assignment (`/api/ops/staff-assignments`)
6. ✅ Play groups / compatibility (`/api/ops/play-groups`)
7. ✅ Feeding schedule management (`/api/ops/feeding-schedules`)

### Models Implemented
- `StaffAssignment` (staff_id, dog_id, booking_id, assignment_date, assignment_type)
- `PlayGroup` (name, dog_ids, scheduled_date, scheduled_time, supervisor_id, compatibility_level)
- `FeedingSchedule` (dog_id, booking_id, frequency, feeding_times, food_type, portion_size)

### Endpoints
```
GET  /api/ops/dashboard - Dogs on site, arrivals, departures, capacity
GET  /api/ops/approval-queue - Bookings requiring approval
POST /api/ops/bookings/{id}/approve
POST /api/ops/bookings/{id}/reject

GET/POST /api/ops/staff-assignments
DELETE /api/ops/staff-assignments/{id}

GET/POST /api/ops/play-groups
PATCH /api/ops/play-groups/{id}
POST /api/ops/play-groups/{id}/add-dog

GET/POST /api/ops/feeding-schedules
PATCH /api/ops/feeding-schedules/{id}
POST /api/ops/feeding-schedules/{id}/log-feeding
```

---

## PHASE 3 - CUSTOMER UX COMPLETION ✅ COMPLETE (Backend)

### Features Implemented
1. ✅ Enhanced booking v2 with pricing engine (`POST /api/bookings/v2`)
2. ✅ Booking modification (`PATCH /api/bookings/{id}/modify`)
3. ✅ Get single booking (`GET /api/bookings/{id}`)
4. ✅ Payment history & invoices (`GET /api/payments/history`, `/api/invoices`)
5. ✅ Customer booking confirmation (`POST /api/bookings/{id}/confirm-payment` - FIXED)

### Endpoints
```
POST /api/bookings/v2 - Enhanced booking with pricing engine, creates invoice
PATCH /api/bookings/{id}/modify - Policy-aware modification
GET /api/bookings/{id} - Get single booking
POST /api/bookings/{id}/confirm-payment - Customer payment confirmation (FIXED)
```

---

## PHASE 4 - AUTOMATION ✅ COMPLETE (Backend)

### Features Implemented
1. ✅ Notification triggers (event-driven)
2. ✅ Notification templates
3. ✅ Automation rules engine
4. ✅ Event logging for automation
5. ✅ Manual notification sending

### Models Implemented
- `NotificationTemplate` (name, notification_type, channel, subject, body, trigger_event)
- `Notification` (user_id, notification_type, channel, subject, body, status)
- `AutomationRule` (name, trigger_event, conditions, actions, active)
- `EventLog` (event_type, event_source, source_id, data, triggered_automations)

### Endpoints
```
GET  /api/notifications
GET  /api/notifications/unread-count
POST /api/notifications/{id}/read
POST /api/notifications/mark-all-read

GET/POST /api/admin/notification-templates
PATCH /api/admin/notification-templates/{id}

GET/POST /api/admin/automation-rules
PATCH/DELETE /api/admin/automation-rules/{id}

GET /api/admin/event-logs
POST /api/admin/send-notification
```

### Default Automation Rules
- Booking Confirmation → In-app notification
- Check-in Reminder (1 day before) → In-app notification
- Payment Received → In-app notification
- Booking Requires Approval → Create task for staff

---

## PHASE 5 - MESSAGING (DEFERRED)

---

## BUG FIXES COMPLETED

### Customer Booking Flow ✅ FIXED
- **Issue:** `POST /api/bookings/{id}/confirm-payment` expected query params but frontend sent JSON body
- **Fix:** Changed endpoint to accept `ConfirmPaymentRequest` body model
- **Status:** Verified working via API testing and customer dashboard

### Staff Booking Flow ✅ VERIFIED WORKING
- `POST /api/bookings/admin` endpoint works correctly for staff/admin users

### Send Notification ✅ FIXED
- **Issue:** `POST /api/admin/send-notification` expected query params but should accept JSON body
- **Fix:** Changed endpoint to accept `SendNotificationRequest` body model

### Get Single Booking ✅ ADDED
- **Issue:** Missing endpoint for `GET /api/bookings/{id}`
- **Fix:** Added new endpoint with proper access control

---

## Test Accounts
- Customer: `customer_test@k9.com` / `Test123!`
- Staff: `staff_test@k9.com` / `Test123!`
- Admin: `admin_test@k9.com` / `Test123!`

## Key Business Rules
- SOFT CAPACITY: Over-capacity bookings allowed but require approval
- 50% DEPOSIT default (admin-configurable)
- Weekend surcharge: 15%
- All pricing server-side (never trust frontend)

---

## Testing Status
- **Test Report:** `/app/test_reports/iteration_4.json`
- **Backend Tests:** 47/47 passed (100%)
- **Test File:** `/app/backend/tests/test_phase2_4.py`

---

## MOCKED INTEGRATIONS
- **Square Payments:** MOCKED - Returns mock payment IDs
- **Email Notifications:** MOCKED - Logged only, not actually sent
- **SMS Notifications:** MOCKED - Logged only, not actually sent

---

## UPCOMING TASKS (Frontend Implementation)

### P1: Staff Ops Frontend (Phase 2 UI)
- Build Daily Capacity Dashboard view
- Arrivals/Departures list
- Booking Approval Queue UI
- Staff Assignment management
- Play Groups management
- Feeding Schedule display

### P2: Customer UX Frontend (Phase 3 UI)
- Multi-step booking with add-ons selection
- Booking modification/cancellation UI
- Payment history page with receipts
- Calendar improvements

### P3: Admin Features Frontend
- Pricing Rules management UI
- Capacity Rules management UI
- Service Definitions management
- Add-Ons configuration
- Policy management

---

## FUTURE/BACKLOG

- Square payments integration (live mode with real API keys)
- Crypto (USDC) payments implementation
- Photo watermarking and purchasing feature
- Native Android and iOS applications
- Phase 5: In-app messaging system
- Email/SMS notification delivery integration

---

## Architecture Notes

### Backend Files
- `/app/backend/server.py` - All API endpoints (4500+ lines - needs refactoring)
- `/app/backend/models.py` - All Pydantic data models
- `/app/backend/pricing_engine.py` - Business logic for cost calculation
- `/app/backend/payment_service.py` - Payment abstraction layer
- `/app/backend/automation_service.py` - Event-driven automation engine
- `/app/backend/auth.py` - JWT authentication

### Frontend Structure
- `/app/frontend/src/pages/` - Page components
- `/app/frontend/src/components/ui/` - Shadcn UI components
- `/app/frontend/src/data/client.js` - Mock data adapter (currently active)

### Refactoring Needed
- Break down `server.py` (4500+ lines) into multiple router files:
  - `routers/auth.py`
  - `routers/bookings.py`
  - `routers/admin.py`
  - `routers/ops.py`
  - `routers/automation.py`
