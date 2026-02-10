# Kennel Operations Platform - PRD

## Original Problem Statement
Build a comprehensive "Kennel Operations 'Single Source of Truth' Platform". This web-first application aims to replace existing tools like Rover and Connecteam by consolidating all business operations into one system.

## Current Tech Stack
- **Frontend:** React 18, Tailwind CSS, Shadcn/UI, Zustand, react-router-dom, recharts
- **Backend:** FastAPI with Pydantic
- **Database:** MongoDB (Motor async driver)
- **Auth:** JWT-based multi-role authentication (Customer, Staff, Admin)
- **Payments:** Square SDK (with mock fallback)

## Migration Plan (PENDING)
The user requested migration to a self-hosted stack:
- PostgreSQL (replacing MongoDB)
- Redis (for caching/sessions)
- Alembic (schema migrations)

**Note:** This migration was started but not completed due to environment constraints. The PostgreSQL files are created but the backend currently runs on MongoDB.

## Core Modules

### 1. Authentication & Authorization ✅
- Multi-role JWT auth (Customer, Staff, Admin)
- Role-based route protection
- Password reset flow

### 2. Customer Portal ✅
- Dashboard with stats
- Dog management (add/edit dogs)
- Booking creation flow
- **NEW:** Calendar page (mock data client)
- **NEW:** Payments page (Square + Crypto coming soon)
- Daily updates viewing

### 3. Staff Portal ✅
- Dashboard with bookings
- Task management
- Timesheet (clock in/out)
- Internal chat

### 4. Admin Portal ✅
- Customer/Staff management
- Booking CRUD
- Timesheet oversight
- Revenue analytics dashboard
- Incident tracking

## What's Been Implemented

### February 10, 2026
- Added frontend data adapter (`/data/client.js`) with mock mode for frontend development
- Created Customer Calendar page (`/customer/calendar`) with day/week views
- Created Customer Payments page (`/customer/payments`) with Square and Crypto (coming soon) options
- Added Calendar and Payments quick action cards to Customer Dashboard

### Previous Sessions
- Full authentication system
- All three portals (Customer, Staff, Admin)
- Revenue analytics dashboard
- Timesheet system with modification requests
- Internal chat system
- Square SDK integration

## Known Issues

### P0 - Critical
1. **Customer Booking Flow** - May fail under certain conditions. Needs verification.

### P1 - Important
1. **Staff Booking Creation** - Needs new flow: search customer → select dogs → create booking → email invoice

## File Structure
```
/app/
├── backend/
│   ├── server.py         # FastAPI endpoints (MongoDB)
│   ├── auth.py           # JWT authentication
│   ├── models.py         # Pydantic models
│   ├── database.py       # PostgreSQL config (for future migration)
│   ├── db_models.py      # SQLAlchemy models (for future migration)
│   ├── schemas.py        # Pydantic schemas (for future migration)
│   └── cache_service.py  # Redis cache service (for future migration)
├── frontend/
│   ├── src/
│   │   ├── data/
│   │   │   └── client.js         # NEW: Mock/API data adapter
│   │   ├── pages/
│   │   │   ├── CustomerCalendarPage.js  # NEW
│   │   │   ├── CustomerPaymentsPage.js  # NEW
│   │   │   ├── CustomerDashboard.js     # Updated with new cards
│   │   │   └── ... (other pages)
│   │   └── App.js               # Updated with new routes
│   └── package.json
└── memory/
    └── PRD.md
```

## Environment Variables
### Backend (.env)
- `MONGO_URL` - MongoDB connection
- `DB_NAME` - Database name
- `JWT_SECRET` - JWT secret key
- `SQUARE_ACCESS_TOKEN` - Square API (optional)
- `DATABASE_URL` - PostgreSQL (for future migration)
- `REDIS_URL` - Redis (for future migration)

### Frontend (.env)
- `REACT_APP_BACKEND_URL` - API endpoint
- `REACT_APP_DATA_MODE` - "mock" or "api" (default: mock)

## Upcoming Tasks

### P1 - High Priority
1. Verify/fix customer booking flow
2. Implement staff booking creation with customer search
3. Complete PostgreSQL migration when proper environment available

### P2 - Medium Priority
1. Staff shift scheduler UI
2. Photo upload feature
3. AI-generated daily summaries (GPT-5.2)

### P3 - Future
- Crypto payments (USDC integration)
- Native mobile apps
- Photo watermarking and purchase system

## Test Accounts
- Customer: `testcustomer@example.com` / `Test123!`
- Register new accounts via `/auth`
