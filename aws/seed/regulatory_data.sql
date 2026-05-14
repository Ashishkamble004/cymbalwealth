-- CymbalWealth: Regulatory Reporting seed data for Redshift Serverless
-- Synthetic quarterly data (Q2-2025 through Q1-2026), amounts in Crores

CREATE SCHEMA IF NOT EXISTS public;

-- ---------------------------------------------------------------------------
-- capital_adequacy — CRAR / Basel III capital ratios per quarter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS capital_adequacy (
    report_date     DATE PRIMARY KEY,
    tier1_capital   DECIMAL(18,2) NOT NULL,
    tier2_capital   DECIMAL(18,2) NOT NULL,
    total_rwa       DECIMAL(18,2) NOT NULL,
    crar_pct        DECIMAL(5,2) NOT NULL,
    min_required    DECIMAL(5,2) DEFAULT 9.00
);

-- ---------------------------------------------------------------------------
-- liquidity_ratios — LCR and NSFR per quarter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS liquidity_ratios (
    report_date     DATE PRIMARY KEY,
    hqla            DECIMAL(18,2) NOT NULL,
    net_cash_30d    DECIMAL(18,2) NOT NULL,
    lcr_pct         DECIMAL(5,2) NOT NULL,
    nsfr_pct        DECIMAL(5,2) NOT NULL
);

-- ---------------------------------------------------------------------------
-- npa_summary — asset quality metrics per quarter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS npa_summary (
    report_date     DATE PRIMARY KEY,
    gross_npa_pct   DECIMAL(5,2) NOT NULL,
    net_npa_pct     DECIMAL(5,2) NOT NULL,
    provision_cov   DECIMAL(5,2) NOT NULL,
    total_advances  DECIMAL(18,2) NOT NULL
);

-- ===========================================================================
-- Seed: capital_adequacy (4 quarters)
-- ===========================================================================
INSERT INTO capital_adequacy (report_date, tier1_capital, tier2_capital, total_rwa, crar_pct, min_required)
VALUES ('2025-06-30', 3980.00, 1050.00, 42500.00, 11.84, 9.00);

INSERT INTO capital_adequacy (report_date, tier1_capital, tier2_capital, total_rwa, crar_pct, min_required)
VALUES ('2025-09-30', 4120.00, 1100.00, 43800.00, 11.92, 9.00);

INSERT INTO capital_adequacy (report_date, tier1_capital, tier2_capital, total_rwa, crar_pct, min_required)
VALUES ('2025-12-31', 4450.00, 1180.00, 44200.00, 12.74, 9.00);

INSERT INTO capital_adequacy (report_date, tier1_capital, tier2_capital, total_rwa, crar_pct, min_required)
VALUES ('2026-03-31', 4820.00, 1240.00, 45900.00, 13.20, 9.00);

-- ===========================================================================
-- Seed: liquidity_ratios (4 quarters)
-- ===========================================================================
INSERT INTO liquidity_ratios (report_date, hqla, net_cash_30d, lcr_pct, nsfr_pct)
VALUES ('2025-06-30', 12500.00, 9200.00, 135.87, 112.40);

INSERT INTO liquidity_ratios (report_date, hqla, net_cash_30d, lcr_pct, nsfr_pct)
VALUES ('2025-09-30', 13100.00, 9500.00, 137.89, 115.20);

INSERT INTO liquidity_ratios (report_date, hqla, net_cash_30d, lcr_pct, nsfr_pct)
VALUES ('2025-12-31', 13800.00, 9800.00, 140.82, 118.50);

INSERT INTO liquidity_ratios (report_date, hqla, net_cash_30d, lcr_pct, nsfr_pct)
VALUES ('2026-03-31', 14200.00, 10000.00, 142.00, 121.30);

-- ===========================================================================
-- Seed: npa_summary (4 quarters)
-- ===========================================================================
INSERT INTO npa_summary (report_date, gross_npa_pct, net_npa_pct, provision_cov, total_advances)
VALUES ('2025-06-30', 3.20, 1.10, 72.50, 38500.00);

INSERT INTO npa_summary (report_date, gross_npa_pct, net_npa_pct, provision_cov, total_advances)
VALUES ('2025-09-30', 2.90, 0.95, 75.20, 39200.00);

INSERT INTO npa_summary (report_date, gross_npa_pct, net_npa_pct, provision_cov, total_advances)
VALUES ('2025-12-31', 2.60, 0.82, 78.40, 40100.00);

INSERT INTO npa_summary (report_date, gross_npa_pct, net_npa_pct, provision_cov, total_advances)
VALUES ('2026-03-31', 2.35, 0.71, 81.20, 41500.00);
