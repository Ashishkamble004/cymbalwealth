-- CymbalWealth: Credit Intelligence seed data for Redshift Serverless
-- Synthetic demo data for 3 customer profiles + loan history

CREATE SCHEMA IF NOT EXISTS public;

-- ---------------------------------------------------------------------------
-- credit_profiles — one row per customer
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS credit_profiles (
    customer_ref    VARCHAR(20) PRIMARY KEY,
    cibil_score     INT NOT NULL,
    credit_grade    VARCHAR(3) NOT NULL,
    active_loans    INT DEFAULT 0,
    total_exposure  DECIMAL(15,2) DEFAULT 0,
    dpd_30          INT DEFAULT 0,
    dpd_90          INT DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT GETDATE()
);

-- ---------------------------------------------------------------------------
-- loan_history — individual loan records per customer
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS loan_history (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    customer_ref    VARCHAR(20) NOT NULL,
    loan_type       VARCHAR(30) NOT NULL,
    sanctioned_amt  DECIMAL(15,2) NOT NULL,
    outstanding_amt DECIMAL(15,2) NOT NULL,
    emi             DECIMAL(10,2) NOT NULL,
    status          VARCHAR(15) NOT NULL,
    opened_at       DATE NOT NULL,
    closed_at       DATE
);

-- ===========================================================================
-- Seed: credit_profiles
-- ===========================================================================

-- CW-2026-001 (Ashish Kamble) — Strong profile
INSERT INTO credit_profiles (customer_ref, cibil_score, credit_grade, active_loans, total_exposure, dpd_30, dpd_90)
VALUES ('CW-2026-001', 742, 'AA', 2, 3250000.00, 0, 0);

-- CW-2026-002 (Priya Sharma) — Moderate profile
INSERT INTO credit_profiles (customer_ref, cibil_score, credit_grade, active_loans, total_exposure, dpd_30, dpd_90)
VALUES ('CW-2026-002', 678, 'BBB', 3, 5800000.00, 1, 0);

-- CW-2026-003 (Raj Patel) — Weak / edge-case profile
INSERT INTO credit_profiles (customer_ref, cibil_score, credit_grade, active_loans, total_exposure, dpd_30, dpd_90)
VALUES ('CW-2026-003', 520, 'C', 4, 8200000.00, 3, 1);

-- ===========================================================================
-- Seed: loan_history
-- ===========================================================================

-- ---- CW-2026-001 (Ashish Kamble) ----
INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-001', 'AUTO', 800000.00, 320000.00, 15800.00, 'ACTIVE', '2023-03-15', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-001', 'CREDIT_CARD', 500000.00, 45000.00, 4500.00, 'ACTIVE', '2022-06-01', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-001', 'PERSONAL', 300000.00, 0.00, 0.00, 'CLOSED', '2021-01-10', '2023-01-10');

-- ---- CW-2026-002 (Priya Sharma) ----
INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-002', 'HOME', 4500000.00, 3900000.00, 42000.00, 'ACTIVE', '2021-09-01', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-002', 'AUTO', 600000.00, 180000.00, 12500.00, 'ACTIVE', '2023-06-15', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-002', 'CREDIT_CARD', 200000.00, 165000.00, 8250.00, 'ACTIVE', '2022-01-20', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-002', 'PERSONAL', 500000.00, 0.00, 0.00, 'CLOSED', '2020-04-01', '2023-04-01');

-- ---- CW-2026-003 (Raj Patel) ----
INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-003', 'HOME', 5000000.00, 4800000.00, 48000.00, 'ACTIVE', '2022-02-01', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-003', 'PERSONAL', 1500000.00, 1400000.00, 35000.00, 'ACTIVE', '2024-01-10', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-003', 'CREDIT_CARD', 300000.00, 290000.00, 14500.00, 'ACTIVE', '2023-08-01', NULL);

INSERT INTO loan_history (customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at)
VALUES ('CW-2026-003', 'AUTO', 700000.00, 650000.00, 18000.00, 'ACTIVE', '2024-06-01', NULL);
