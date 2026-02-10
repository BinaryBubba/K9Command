# K9Command - PRD

## Original Problem Statement
K9Command is a single-facility, staff-operated dog boarding/daycare platform with customer self-service, internal staff operations tooling, and automation-first design. The goal is Rover-parity for a single facility.

## Tech Stack
- **Frontend:** React 18, Tailwind CSS, Shadcn/UI, Zustand
- **Backend:** FastAPI with Pydantic, MongoDB (Motor async)
- **Auth:** JWT multi-role (Customer, Staff, Admin)
- **Payments:** Square SDK (primary), Crypto infrastructure (USDC - deferred)

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

### Default Data Seeded
- 2 Service Types: Standard Boarding ($50/dog/day), Daycare ($35/dog)
- 4 Add-Ons: Extra Playtime, Bath, Transport, Feeding
- 3 Cancellation Policies: 7-day, 3-day, last-minute
- 1 Pricing Rule: Weekend surcharge (15%)
- System Settings: deposit_percentage=50, tax_rate=0, etc.

### Backend Files
- `/app/backend/pricing_engine.py` - Authoritative pricing calculation
- `/app/backend/payment_service.py` - Payment abstraction (Square + Crypto infrastructure)
- `/app/backend/models.py` - All Phase 1 models
- `/app/backend/server.py` - All Phase 1 endpoints

---

## PHASE 2 - STAFF OPERATIONS 🔜 NEXT

### Required Features
1. Daily capacity dashboard ("Dogs on site today")
2. Upcoming arrivals/departures view
3. Booking approval queue
4. Dog ↔ Staff assignment
5. Play groups / compatibility
6. Feeding schedule display

### Required Models
- StaffAssignment (dog_id, staff_id, date)
- PlayGroup (dogs[], compatibility_notes)
- FeedingSchedule (dog_id, times[], instructions)

---

## PHASE 3 - CUSTOMER UX COMPLETION

### Required Features
1. Multi-step booking with add-ons selection
2. Booking modification (policy-aware)
3. Payment history & downloadable receipts
4. Calendar polish

---

## PHASE 4 - AUTOMATION

### Required Features
1. Notification triggers
2. Task scaffolding
3. Event logging for automation

---

## PHASE 5 - MESSAGING (DEFERRED)

---

## Test Accounts
- Customer: `testcustomer@example.com` / `Test123!`

## Key Business Rules
- SOFT CAPACITY: Over-capacity bookings allowed but require approval
- 50% DEPOSIT default (admin-configurable)
- Weekend surcharge: 15%
- All pricing server-side (never trust frontend)
