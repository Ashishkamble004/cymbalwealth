# Fake/Simulated Code Detection Report

**Scanned:** wm1 codebase (Cymbal Wealth)  
**Date:** 31 March 2026  
**Findings:** 19 (2 Critical, 7 Medium, 8 Low)

---

## Critical

### 1. Hardcoded Customer Database
- **File:** `backend/kyc_agent/sub_agents/verification_agent.py` (lines 14-40)
- **Issue:** Static Python dict with only 2 customer records. All verification functions operate against this.
- **Replace with:** Real database (Cloud SQL, Firestore) or CRM API.

### 2. Hardcoded Login Validation
- **File:** `frontend/components/LoginPage.tsx` (lines 3-4, 25)
- **Issue:** `VALID_REFS = ["CW-2026-001", "CW-2026-002"]` — client-side validation only.
- **Replace with:** Backend API call to validate reference numbers.

---

## Medium

### 4. Hardcoded Verification Payload
- **File:** `demo-portal/home-loan-verification.html` (lines 304-311)
- **Issue:** Always sends "Ashish Kamble", "EWIPK1035H" regardless of actual user.
- **Replace with:** Collect from form inputs or authenticated session.

### 5. Pre-filled Form Values
- **File:** `demo-portal/home-loan.html` (lines 112-151)
- **Issue:** Hardcoded employer "Nexagen Technologies", salary "1,50,000", etc.
- **Replace with:** Fetch from user profile API.

### 6. Hardcoded Property Details
- **File:** `demo-portal/home-loan-property.html` (lines 79-103)
- **Issue:** Static values for Lodha Palava, ₹95L, RERA number.
- **Replace with:** Empty form or saved application state.

### 7. Static Dashboard
- **File:** `demo-portal/dashboard.html` (lines 77-331)
- **Issue:** All account balances (₹12,45,892), FDs, MFs, transactions are hardcoded HTML.
- **Replace with:** Backend API for account data.

### 8. Hardcoded Approval Values
- **File:** `demo-portal/home-loan-verification.html` (lines 436-520)
- **Issue:** Pre-approved ₹75L, 8.35%, ₹64,230 EMI — never changes.
- **Replace with:** Values from eligibility assessor agent response.

### 9. Hardcoded PAN in Upload Request
- **File:** `demo-portal/home-loan-documents.html` (line 255)
- **Issue:** `applicant_pan: 'EWIPK1035H'` hardcoded in signed URL request.
- **Replace with:** From authenticated session.

### 14. InMemorySessionService
- **Files:** `backend/main.py:68`, `backend/home_loan_api.py:34`
- **Issue:** ADK sessions stored in memory — lost on restart, no horizontal scaling.
- **Replace with:** Persistent session store (Firestore, Redis).

### 15. In-Process Frame Storage
- **File:** `backend/session_frames.py`
- **Issue:** Video frames stored in Python dict — single instance only.
- **Replace with:** Redis or shared store for multi-instance.

### 16. Wildcard CORS
- **Files:** `backend/main.py:62`, `backend/homeloan_main.py:34`
- **Issue:** `allow_origins=["*"]` — allows any domain.
- **Replace with:** Restrict to actual frontend domain.

---

## Low

### 3. Simulated Login Delay
- **File:** `frontend/components/LoginPage.tsx` (lines 33-37)
- **Issue:** 500ms setTimeout fakes loading.

### 10. sessionStorage as Data Bus
- **Files:** `demo-portal/home-loan-documents.html`, `home-loan-verification.html`
- **Issue:** Doc info passed between pages via sessionStorage.

### 11. Hardcoded User Initials "AK"
- **Files:** All demo-portal nav bars (5 files)
- **Issue:** Avatar always shows "AK" / "Ashish Kamble".

### 12. Static Eligibility Sidebar
- **File:** `demo-portal/home-loan.html` (lines 253-275)
- **Issue:** Shows ₹1.2Cr, 8.35%, ₹64,230 EMI — not connected to sliders.

### 13. Inconsistent Salary Amount
- **File:** `demo-portal/home-loan-property.html` (line 50)
- **Issue:** Shows "income of ₹2,85,000/month" but salary is ₹1,50,000 on previous page.

### 17. Hardcoded GCP Defaults
- **Files:** `backend/main.py`, `storage_utils.py`, `home_loan_api.py`
- **Issue:** Fallback values "general-ak", "cymbal-wealth" hardcoded.

### 18. Localhost WebSocket Fallback
- **File:** `frontend/hooks/useLiveSessionWebSocket.ts` (line 22)
- **Issue:** Falls back to `ws://localhost:8080` if env var missing.

### 19. Demo Reference Buttons Visible
- **File:** `frontend/components/LoginPage.tsx` (lines 200-219)
- **Issue:** Clickable demo ref numbers shown on login page.
