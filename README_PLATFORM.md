# Kennel Operations Platform - Single Source of Truth

## 🎯 Overview
A comprehensive web-first platform designed to serve as the single source of truth for multi-location dog kennel businesses. This platform replaces both Rover (customer-facing) and Connecteam (staff operations) with a unified, modern solution.

## ✨ Key Features Implemented

### 1. **Customer Portal**
- 🏠 Beautiful landing page with warm, pet-focused design
- 👤 Secure registration and authentication
- 🐕 Dog profile management (breeds, vaccinations, behavioral notes, medical flags)
- 📅 Booking system with automatic price calculation
- 📸 Daily photo updates feed with AI-generated summaries
- 💳 Payment history tracking (Square integration ready)
- ⭐ Review submission system

### 2. **Staff Dashboard**
- ⏰ Clock in/out time tracking
- ✅ Daily task checklists with completion tracking
- 📷 Photo upload workflow for daily updates
- 📋 View active bookings and guest lists
- 📝 Internal notes and SOP access
- 🔄 Offline-capable design (prepared for future mobile apps)

### 3. **Admin Panel**
- 📊 Comprehensive dashboard with key metrics:
  - Total customers, dogs, bookings
  - Active bookings
  - Staff count
- 👥 Customer & dog management
- 📅 Booking calendar and capacity management
- 🧑‍💼 Staff scheduling and management
- 🚨 Incident reporting and tracking
- 📜 Immutable audit logs (7-year retention ready)
- 📈 Reports & analytics foundation

### 4. **Daily Photo Updates (Core Innovation)**
- Staff upload photos/videos throughout the day
- AI-powered summaries using **GPT-5.2** (via Emergent LLM Key)
- Warm, personalized messages for each household
- Approval workflow before sending
- Scheduled delivery (~2pm daily)
- Multi-channel delivery (in-app, email, SMS ready)

### 5. **Security & Compliance**
- 🔒 JWT-based authentication
- 🛡️ Role-based access control (Customer, Staff, Admin)
- 📝 Immutable audit logging for all critical actions
- 🚨 Incident reporting with evidence attachment
- 📅 7-year data retention architecture
- 🔐 Secure password hashing with bcrypt

## 🎨 Design System

### Colors
- **Primary (Sage Green)**: `#4A7C59` - Trust, nature, calm
- **Secondary (Goldenrod)**: `#F4B942` - Joy, warmth, energy
- **Background**: `#F9F7F2` - Soft, warm cream

### Typography
- **Headings**: Fraunces (Serif) - Emotional, premium feel
- **Body**: Manrope (Sans-serif) - Clean, readable
- **Code/Logs**: JetBrains Mono (Monospace)

### Design Principles
- Warm and friendly aesthetic (pet-focused)
- Professional yet approachable
- Generous spacing for breathing room
- Micro-animations for delightful interactions
- Mobile-first for staff dashboard

## 🏗️ Technical Architecture

### Backend (FastAPI + MongoDB)
```
/app/backend/
├── server.py          # Main FastAPI application with all endpoints
├── models.py          # Pydantic models for all entities
├── auth.py            # JWT authentication & authorization
├── ai_service.py      # GPT-5.2 integration for summaries
└── .env               # Environment configuration
```

**Key Models:**
- User (Customer, Staff, Admin)
- Dog (with household grouping)
- Booking (with capacity & pricing)
- DailyUpdate (with AI summaries)
- Task (for staff operations)
- TimeEntry (clock in/out)
- Incident (compliance & safety)
- AuditLog (immutable records)
- Review (customer feedback)

**API Endpoints (30+):**
- `/api/auth/*` - Registration, login, token refresh
- `/api/dogs/*` - Dog profile CRUD
- `/api/bookings/*` - Reservation management
- `/api/daily-updates/*` - Photo uploads & AI summaries
- `/api/tasks/*` - Staff task management
- `/api/time-entries/*` - Time tracking
- `/api/incidents/*` - Incident reporting
- `/api/reviews/*` - Review collection
- `/api/audit-logs/*` - Compliance logging
- `/api/dashboard/stats` - Role-specific statistics

### Frontend (React + TailwindCSS)
```
/app/frontend/src/
├── App.js                    # Main routing & protected routes
├── pages/
│   ├── LandingPage.js       # Marketing homepage
│   ├── AuthPage.js          # Login/Register
│   ├── CustomerDashboard.js # Customer portal
│   ├── StaffDashboard.js    # Staff operations
│   └── AdminDashboard.js    # Admin panel
├── components/
│   ├── AuthForm.js          # Reusable auth component
│   └── ui/                  # Shadcn/UI components
├── store/
│   └── authStore.js         # Zustand state management
└── utils/
    └── api.js               # Axios instance with auth
```

### Database Schema (MongoDB)
- `users` - All user accounts (customers, staff, admins)
- `dogs` - Dog profiles linked to households
- `bookings` - Reservations with dates & pricing
- `daily_updates` - Photo/video updates with AI summaries
- `tasks` - Staff task assignments
- `time_entries` - Staff clock in/out records
- `incidents` - Safety and incident reports
- `audit_logs` - Immutable activity logs
- `reviews` - Customer feedback

## 🔑 Environment Variables

### Backend (.env)
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
CORS_ORIGINS=*
EMERGENT_LLM_KEY=sk-emergent-xxx (for GPT-5.2)
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DAYS=30
```

### Frontend (.env)
```env
REACT_APP_BACKEND_URL=https://paws-point.preview.emergentagent.com
```

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB
- Yarn

### Installation
```bash
# Backend
cd /app/backend
pip install -r requirements.txt

# Frontend
cd /app/frontend
yarn install
```

### Running
Services are managed by supervisor and run automatically:
- Backend: http://0.0.0.0:8001
- Frontend: http://localhost:3000

### Test Accounts
Create accounts via the registration page at `/auth`:
1. Customer: Select "Dog Parent"
2. Staff: Select "Staff Member"
3. Admin: Select "Administrator"

## 🧪 Testing Results

**Test Coverage: 98% Success Rate**
- ✅ Backend API: 100% (29/29 endpoints)
- ✅ Frontend UI: 95% (all critical flows)
- ✅ Integration: 100% (auth, data flow, AI generation)

**Tested Scenarios:**
- Multi-role authentication and authorization
- Dog profile creation and management
- Booking creation with price calculation
- Daily update creation with AI summary generation
- Staff clock in/out workflow
- Task assignment and completion
- Audit log creation
- Role-based dashboard access

## 🔄 Key User Flows

### Customer Flow
1. Register → Add Dogs → Book Stay → Receive Daily Updates → Submit Review

### Staff Flow
1. Clock In → View Tasks → Upload Photos → Generate AI Summary → Approve Update → Clock Out

### Admin Flow
1. Login → View Dashboard Stats → Manage Bookings → Review Incidents → Check Audit Logs

## 🎯 Core Innovations

### 1. AI-Powered Daily Updates
- **Unique Value**: Automated, personalized summaries using GPT-5.2
- **Implementation**: `emergentintegrations` library with OpenAI
- **Output**: Warm, friendly 2-3 sentence summaries per household
- **Example**: "Max and Bella had a wonderful day! They spent the morning playing fetch in the sunshine, enjoyed their favorite treats at lunch, and made lots of new furry friends during group playtime."

### 2. Single Source of Truth
- All data centralized in one platform
- No data duplication between systems
- Real-time synchronization across all portals
- Immutable audit trail for compliance

### 3. Multi-Tenant Architecture
- Currently single location
- Designed for multi-location expansion
- Location-specific staff assignments
- Shared customer households across locations

## 📋 Future Enhancements (Post-MVP)

### Phase 2
- [ ] Mobile apps (Android & iOS)
- [ ] Offline mode with sync for staff
- [ ] Email/SMS delivery for daily updates
- [ ] Advanced booking calendar with drag-drop
- [ ] Real Square payment integration
- [ ] Photo/video storage on S3/CloudStorage

### Phase 3
- [ ] Multi-location management
- [ ] Advanced reporting & analytics
- [ ] Customer mobile app
- [ ] Review integration with Google Business Profile
- [ ] Automated capacity management
- [ ] Dynamic pricing rules

### Phase 4
- [ ] SaaS platform for other kennels
- [ ] White-label customization
- [ ] API for third-party integrations
- [ ] Advanced AI features (health monitoring, behavior analysis)

## 🔐 Security Notes

### Production Considerations
1. **Change JWT_SECRET** to a strong random value
2. **Enable HTTPS** for all communication
3. **Configure CORS_ORIGINS** to specific domains
4. **Implement rate limiting** on auth endpoints
5. **Use environment-specific MongoDB** credentials
6. **Enable MongoDB authentication**
7. **Implement file upload to S3** (not base64 in DB)
8. **Add email verification** for registrations
9. **Implement password reset** flow
10. **Enable 2FA for admin accounts**

## 📊 API Documentation

### Authentication
```bash
# Register
POST /api/auth/register
Body: { email, password, full_name, phone?, role }
Response: { token, user }

# Login
POST /api/auth/login
Body: { email, password }
Response: { token, user }

# Get Current User
GET /api/auth/me
Headers: { Authorization: Bearer <token> }
Response: { user }
```

### Dogs
```bash
# Create Dog
POST /api/dogs
Headers: { Authorization: Bearer <token> }
Body: { name, breed, age?, weight?, behavioral_notes? }
Response: { dog }

# List Dogs
GET /api/dogs
Headers: { Authorization: Bearer <token> }
Response: [{ dog }]
```

### Bookings
```bash
# Create Booking
POST /api/bookings
Headers: { Authorization: Bearer <token> }
Body: { dog_ids[], location_id, check_in_date, check_out_date, notes? }
Response: { booking }

# List Bookings
GET /api/bookings
Headers: { Authorization: Bearer <token> }
Response: [{ booking }]
```

## 🎨 Component Library

Using **Shadcn/UI** components:
- Button, Card, Input, Label
- Checkbox, Select, Dialog
- Accordion, Tabs, Toast
- All styled with TailwindCSS

## 📝 Notes

### Mocked Features
- **Square Payment**: Mock integration in place, ready for API keys
- **Media Storage**: Currently base64 in DB (replace with S3 in production)
- **Email/SMS Delivery**: Infrastructure ready, needs provider integration

### Known Limitations
- Media upload limited by base64 storage (temporary)
- No actual payment processing (mocked)
- Single location in current setup
- No mobile apps yet (web-first approach)

## 🤝 Support

For issues or questions:
- Check `/app/test_reports/iteration_1.json` for test results
- Review backend logs: `tail -f /var/log/supervisor/backend.*.log`
- Review frontend logs in browser console

## 📄 License

Internal project for kennel operations. Not licensed for external use.

---

**Built with ❤️ for dog parents and kennel operators**
