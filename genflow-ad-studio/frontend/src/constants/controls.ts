import type { GeminiModelOption } from '../types';

// ─── CymbalWealth Banking Product Categories ────────────────
export const CW_PRODUCT_CATEGORIES = [
  { id: 'savings_account',    label: 'Savings Account',       description: 'Zero-fee savings with 7% p.a.' },
  { id: 'current_account',   label: 'Current Account',        description: 'Business & premium current accounts' },
  { id: 'credit_card',       label: 'Credit Card',            description: 'Rewards, cashback & travel cards' },
  { id: 'fixed_deposit',     label: 'Fixed Deposit (FD)',     description: 'Up to 8.5% p.a. assured returns' },
  { id: 'recurring_deposit', label: 'Recurring Deposit (RD)', description: 'Disciplined monthly investing' },
  { id: 'home_loan',         label: 'Home Loan',              description: 'Rates from 8.35% p.a.' },
  { id: 'personal_loan',     label: 'Personal Loan',          description: 'Instant approval up to ₹50L' },
  { id: 'wealth_privilege',  label: 'Wealth Privilege',       description: 'Exclusive private banking membership' },
  { id: 'investment_advisory', label: 'Investment Advisory',  description: 'Personalised portfolio strategies' },
  { id: 'portfolio_mgmt',    label: 'Portfolio Management',   description: 'Active management & rebalancing' },
  { id: 'tax_optimization',  label: 'Tax Optimization',       description: 'Maximise post-tax returns' },
] as const;

export type CWProductCategoryId = typeof CW_PRODUCT_CATEGORIES[number]['id'];

// Pre-filled product details for each category
export const CW_PRODUCT_DETAILS: Record<string, { product_name: string; specifications: string }> = {
  savings_account:    { product_name: 'CymbalWealth Savings Account', specifications: 'Zero account maintenance fee. 7% p.a. interest on daily balance. Instant account opening via Video KYC. Free unlimited NEFT/RTGS/IMPS. Linked Debit Card with ₹2L daily limit. Auto-sweep FD on balance above ₹1L.' },
  current_account:   { product_name: 'CymbalWealth Current Account', specifications: 'Business current account with zero transaction charges. Dedicated relationship manager. Bulk payment APIs. Overdraft facility up to ₹25L. Multi-city cheque collection.' },
  credit_card:       { product_name: 'CymbalWealth Signature Credit Card', specifications: '5X reward points on dining and travel. 2% unlimited cashback on all spends. Complimentary airport lounge access. Zero foreign transaction fee. ₹10L credit limit. Contactless & virtual card.' },
  fixed_deposit:     { product_name: 'CymbalWealth Fixed Deposit', specifications: 'Up to 8.5% p.a. for 2-year tenure. Guaranteed returns. Premature withdrawal available. Loan against FD up to 90% of value. Auto-renewal option. ₹10,000 minimum deposit.' },
  recurring_deposit: { product_name: 'CymbalWealth Recurring Deposit', specifications: 'Monthly deposit from ₹500. 7.8% p.a. on 12-month RD. Auto-debit from savings account. Premature closure after 3 months. Goal-based RD planner integrated.' },
  home_loan:         { product_name: 'CymbalWealth Home Loan', specifications: 'Interest rate from 8.35% p.a. Up to ₹5 crore loan amount. 30-year tenure. No prepayment penalty. Balance transfer with top-up. AI-based document verification. Approval in 24 hours.' },
  personal_loan:     { product_name: 'CymbalWealth Personal Loan', specifications: 'Instant approval in 10 minutes. Loan amount ₹50,000 to ₹50L. Rate from 10.5% p.a. Zero collateral. Flexible 12–60 month tenure. Fully digital disbursement.' },
  wealth_privilege:  { product_name: 'CymbalWealth Wealth Privilege', specifications: 'Exclusive invite-only banking membership. Dedicated private banker. Priority branch & phone support. Pre-approved credit up to ₹2Cr. Quarterly wealth review. Concierge services. Complimentary WILL drafting.' },
  investment_advisory: { product_name: 'CymbalWealth Investment Advisory', specifications: 'AI-powered personalised investment plans. ₹500 SIP starting point. Access to direct mutual funds, PMS & AIF. Risk profiling engine. Tax-harvesting alerts. Dedicated wealth advisor.' },
  portfolio_mgmt:    { product_name: 'CymbalWealth Portfolio Management', specifications: 'Active portfolio management by SEBI-registered PMS. Minimum ₹50L. Multi-asset allocation — equities, debt, gold, REITs. Real-time dashboard. Annual returns target 15–18% CAGR.' },
  tax_optimization:  { product_name: 'CymbalWealth Tax Optimization', specifications: 'Integrated tax-loss harvesting. Section 80C, 80D, 54EC planning. Automated ITR preparation. Capital gains optimisation. Available as add-on with any investment account.' },
};

// ─── Ad Tones (banking-appropriate) ────────────────────────
export const AD_TONES = ['sophisticated', 'warm', 'authoritative', 'aspirational', 'trustworthy'];

// ─── Gemini Models (Script Generation) ──────────────────────
export const GEMINI_MODELS: GeminiModelOption[] = [
  { id: 'gemini-3-pro-preview', label: 'Gemini 3.1 Pro', description: 'Premium quality' },
  { id: 'gemini-3-flash-preview', label: 'Gemini 3.1 Flash', description: 'Fast & capable (default)' },
  { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', description: 'Stable' },
  { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', description: 'Fastest' },
];

// ─── Customer Segments ──────────────────────────────────────
export const CW_CUSTOMER_SEGMENTS = [
  { id: 'young_professional', label: 'Young Professional', description: 'First job, building wealth, 22–30 yrs' },
  { id: 'newly_married',      label: 'Newly Married',      description: 'Joint finances, home purchase planning' },
  { id: 'new_parent',         label: 'New Parent',         description: 'Child education & insurance planning' },
  { id: 'mid_career',         label: 'Mid-Career Professional', description: 'Growing wealth, 31–45 yrs' },
  { id: 'hni',                label: 'HNI / Affluent',     description: 'High Net Worth, premium products' },
  { id: 'uhni',               label: 'UHNI',               description: 'Ultra HNI, Wealth Privilege tier' },
  { id: 'pre_retirement',     label: 'Pre-Retirement',     description: 'Capital preservation, 50–60 yrs' },
  { id: 'senior_citizen',     label: 'Senior Citizen',     description: 'FD, stable income, 60+ yrs' },
  { id: 'nri',                label: 'NRI',                 description: 'Non-Resident Indian, forex & remittance' },
  { id: 'student',            label: 'Student',             description: 'First savings account, campus offers' },
] as const;

export const CW_INCOME_TIERS = ['Mass Market', 'Emerging Affluent', 'HNI', 'UHNI'] as const;

export const CW_LIFE_STAGES = [
  'First Job', 'Newly Married', 'New Parent', 'Growing Family',
  'Pre-Retirement', 'Retired', 'NRI Returnee',
] as const;

export const CW_KEY_MOTIVATIONS = [
  'Wealth Growth', 'Tax Saving', 'Home Ownership', 'Child Education',
  'Retirement Planning', 'Legacy Planning', 'Easy Credit', 'Exclusive Privileges',
] as const;

export const CW_LANGUAGES = ['English', 'Hindi', 'Hinglish', 'Tamil', 'Telugu', 'Kannada', 'Marathi', 'Bengali'] as const;

export const CW_LOCATION_TYPES = ['Metro', 'Tier-2 City', 'Tier-3 City / Rural'] as const;

// ─── Ethnicities ────────────────────────────────────────────
export const ETHNICITIES = [
  '', 'South Asian', 'East Asian', 'Southeast Asian', 'Black', 'White',
  'Latino', 'Middle Eastern', 'Mixed',
];

// ─── Age Ranges ─────────────────────────────────────────────
export const AGE_RANGES = ['18-25', '25-35', '35-45', '45-55', '55+'];

// ─── Veo Models (Video Generation) ──────────────────────────
export const VEO_MODELS = [
  { id: 'veo-3.1-generate-preview', label: 'Veo 3.1 Preview', description: 'Standard — Best quality' },
  { id: 'veo-3.1-fast-generate-preview', label: 'Veo 3.1 Fast Preview', description: 'Faster generation' },
];

// ─── Image Resolutions ──────────────────────────────────────
export const IMAGE_RESOLUTIONS = ['1K', '2K', '4K'] as const;

// ─── Defaults ───────────────────────────────────────────────
export const DEFAULT_IMAGE_RESOLUTION = '2K';
export const DEFAULT_STORYBOARD_QC_THRESHOLD = 60;
export const DEFAULT_MAX_REGEN_ATTEMPTS = 3;
export const DEFAULT_VIDEO_QC_THRESHOLD = 3;
export const DEFAULT_MAX_VIDEO_QC_REGEN = 2;
export const DEFAULT_NUM_VIDEO_VARIANTS = 1;
export const DEFAULT_NUM_AVATAR_VARIANTS = 2;
