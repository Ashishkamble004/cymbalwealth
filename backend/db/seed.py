"""
Database Seed — 5 realistic Indian wealth management clients
"""

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session
from db.database import SessionLocal, engine, Base
from models.client import Client, Holding, Goal
from models.transaction import Transaction, Interaction

logger = logging.getLogger(__name__)


def seed_data():
    """Populate the database with 5 realistic client profiles."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if data already exists
    if db.query(Client).count() > 0:
        logger.info("Database already seeded — skipping")
        db.close()
        return

    today = date.today()

    # =========================================================================
    # Client 1: Arjun Mehta — UHNI, ₹62 Cr, Aggressive
    # =========================================================================
    c1 = Client(
        name="Arjun Mehta", email="arjun.mehta@example.com", phone="+91-98765-43210",
        dob=date(1972, 3, 15), pan="ABCPM1234A", aadhaar_last4="7821",
        address="14 Altamount Road, South Mumbai, Maharashtra 400026",
        segment="UHNI", risk_profile="Aggressive", kyc_status="verified",
        annual_income=85000000, aum=620000000, rm_name="Vikram Sharma",
    )
    db.add(c1)
    db.flush()

    c1_holdings = [
        Holding(client_id=c1.id, instrument_name="Reliance Industries", instrument_type="Equity", quantity=15000, purchase_price=2180, current_price=2952, purchase_date=date(2023, 6, 15)),
        Holding(client_id=c1.id, instrument_name="HDFC Bank", instrument_type="Equity", quantity=12000, purchase_price=1520, current_price=1685, purchase_date=date(2023, 4, 10)),
        Holding(client_id=c1.id, instrument_name="Infosys", instrument_type="Equity", quantity=8000, purchase_price=1380, current_price=1842, purchase_date=date(2023, 7, 22)),
        Holding(client_id=c1.id, instrument_name="ICICI Prudential Bluechip Fund", instrument_type="MF", quantity=250000, purchase_price=78, current_price=92.5, purchase_date=date(2023, 3, 1)),
        Holding(client_id=c1.id, instrument_name="UTI Nifty 50 Index Fund", instrument_type="MF", quantity=180000, purchase_price=142, current_price=168, purchase_date=date(2023, 5, 15)),
        Holding(client_id=c1.id, instrument_name="HDFC Flexi Cap Fund", instrument_type="MF", quantity=200000, purchase_price=35, current_price=42.8, purchase_date=date(2023, 2, 10)),
        Holding(client_id=c1.id, instrument_name="SBI Corporate Bond Fund", instrument_type="Bond", quantity=300000, purchase_price=42, current_price=44.5, purchase_date=date(2023, 8, 5)),
        Holding(client_id=c1.id, instrument_name="Sovereign Gold Bond 2028", instrument_type="Gold", quantity=500, purchase_price=5200, current_price=7240, purchase_date=date(2023, 3, 20)),
        Holding(client_id=c1.id, instrument_name="Motilal Oswal Nasdaq 100 FOF", instrument_type="MF", quantity=100000, purchase_price=28, current_price=38.2, purchase_date=date(2023, 4, 5)),
        Holding(client_id=c1.id, instrument_name="TechStartup Pvt Ltd (Unlisted)", instrument_type="Alternate", quantity=50000, purchase_price=120, current_price=185, purchase_date=date(2022, 11, 15)),
        Holding(client_id=c1.id, instrument_name="Titan Company", instrument_type="Equity", quantity=5000, purchase_price=2850, current_price=3620, purchase_date=date(2023, 9, 1)),
        Holding(client_id=c1.id, instrument_name="Bajaj Finance", instrument_type="Equity", quantity=3000, purchase_price=6800, current_price=7450, purchase_date=date(2023, 5, 20)),
    ]
    db.add_all(c1_holdings)

    c1_goals = [
        Goal(client_id=c1.id, name="Business Exit Corpus", target_amount=2000000000, current_amount=620000000, target_year=2030),
        Goal(client_id=c1.id, name="Son's Harvard MBA 2027", target_amount=30000000, current_amount=18000000, target_year=2027),
    ]
    db.add_all(c1_goals)

    c1_txns = [
        Transaction(client_id=c1.id, instrument_name="Reliance Industries", transaction_type="BUY", quantity=5000, price=2180, amount=10900000, transaction_date=today - timedelta(days=150), notes="Lump-sum purchase"),
        Transaction(client_id=c1.id, instrument_name="ICICI Prudential Bluechip Fund", transaction_type="SIP", quantity=12820, price=78, amount=1000000, transaction_date=today - timedelta(days=120)),
        Transaction(client_id=c1.id, instrument_name="HDFC Bank", transaction_type="DIVIDEND", quantity=0, price=0, amount=192000, transaction_date=today - timedelta(days=90), notes="Quarterly dividend"),
        Transaction(client_id=c1.id, instrument_name="UTI Nifty 50 Index Fund", transaction_type="SIP", quantity=7042, price=142, amount=1000000, transaction_date=today - timedelta(days=60)),
        Transaction(client_id=c1.id, instrument_name="TechStartup Pvt Ltd (Unlisted)", transaction_type="BUY", quantity=10000, price=150, amount=1500000, transaction_date=today - timedelta(days=45), notes="Pre-Series B top-up"),
        Transaction(client_id=c1.id, instrument_name="SBI Corporate Bond Fund", transaction_type="REDEMPTION", quantity=50000, price=44, amount=2200000, transaction_date=today - timedelta(days=30)),
    ]
    db.add_all(c1_txns)

    c1_interactions = [
        Interaction(client_id=c1.id, interaction_type="call", summary="Discussed business exit timeline. Client considering partial stake sale in Q2 2025.", interaction_date=today - timedelta(days=14)),
        Interaction(client_id=c1.id, interaction_type="meeting", summary="Annual portfolio review. Client happy with equity returns, wants to increase alternate allocation.", interaction_date=today - timedelta(days=45)),
        Interaction(client_id=c1.id, interaction_type="email", summary="Sent Harvard MBA cost analysis and education fund projections.", interaction_date=today - timedelta(days=60)),
    ]
    db.add_all(c1_interactions)

    # =========================================================================
    # Client 2: Priya Nair — HNI, ₹7.4 Cr, Moderate
    # =========================================================================
    c2 = Client(
        name="Priya Nair", email="priya.nair@example.com", phone="+91-98765-11111",
        dob=date(1980, 8, 22), pan="BNCPN5678B", aadhaar_last4="3456",
        address="42 Koramangala 4th Block, Bengaluru, Karnataka 560034",
        segment="HNI", risk_profile="Moderate", kyc_status="verified",
        annual_income=12000000, aum=74000000, rm_name="Vikram Sharma",
    )
    db.add(c2)
    db.flush()

    c2_holdings = [
        Holding(client_id=c2.id, instrument_name="HDFC Bank", instrument_type="Equity", quantity=4000, purchase_price=1450, current_price=1685, purchase_date=date(2023, 5, 10)),
        Holding(client_id=c2.id, instrument_name="Infosys", instrument_type="Equity", quantity=3500, purchase_price=1420, current_price=1842, purchase_date=date(2023, 3, 15)),
        Holding(client_id=c2.id, instrument_name="UTI Nifty 50 Index Fund", instrument_type="MF", quantity=80000, purchase_price=140, current_price=168, purchase_date=date(2023, 4, 1)),
        Holding(client_id=c2.id, instrument_name="HDFC Flexi Cap Fund", instrument_type="MF", quantity=120000, purchase_price=34, current_price=42.8, purchase_date=date(2023, 6, 1)),
        Holding(client_id=c2.id, instrument_name="SBI Corporate Bond Fund", instrument_type="Bond", quantity=200000, purchase_price=41.5, current_price=44.5, purchase_date=date(2023, 7, 15)),
        Holding(client_id=c2.id, instrument_name="Sovereign Gold Bond 2029", instrument_type="Gold", quantity=200, purchase_price=5400, current_price=7240, purchase_date=date(2023, 6, 20)),
        Holding(client_id=c2.id, instrument_name="ICICI Prudential Bluechip Fund", instrument_type="MF", quantity=80000, purchase_price=76, current_price=92.5, purchase_date=date(2023, 8, 1)),
        Holding(client_id=c2.id, instrument_name="Reliance Industries", instrument_type="Equity", quantity=2000, purchase_price=2350, current_price=2952, purchase_date=date(2023, 9, 10)),
        Holding(client_id=c2.id, instrument_name="Motilal Oswal Nasdaq 100 FOF", instrument_type="MF", quantity=40000, purchase_price=30, current_price=38.2, purchase_date=date(2023, 5, 20)),
        Holding(client_id=c2.id, instrument_name="Titan Company", instrument_type="Equity", quantity=1500, purchase_price=2750, current_price=3620, purchase_date=date(2023, 10, 5)),
    ]
    db.add_all(c2_holdings)

    c2_goals = [
        Goal(client_id=c2.id, name="Retirement Corpus", target_amount=150000000, current_amount=74000000, target_year=2035),
        Goal(client_id=c2.id, name="Second Home in Goa", target_amount=25000000, current_amount=12000000, target_year=2026),
    ]
    db.add_all(c2_goals)

    c2_txns = [
        Transaction(client_id=c2.id, instrument_name="UTI Nifty 50 Index Fund", transaction_type="SIP", quantity=3571, price=140, amount=500000, transaction_date=today - timedelta(days=150)),
        Transaction(client_id=c2.id, instrument_name="HDFC Flexi Cap Fund", transaction_type="SIP", quantity=14705, price=34, amount=500000, transaction_date=today - timedelta(days=120)),
        Transaction(client_id=c2.id, instrument_name="Infosys", transaction_type="DIVIDEND", quantity=0, price=0, amount=63000, transaction_date=today - timedelta(days=100)),
        Transaction(client_id=c2.id, instrument_name="Reliance Industries", transaction_type="BUY", quantity=500, price=2350, amount=1175000, transaction_date=today - timedelta(days=75)),
        Transaction(client_id=c2.id, instrument_name="SBI Corporate Bond Fund", transaction_type="SIP", quantity=12048, price=41.5, amount=500000, transaction_date=today - timedelta(days=45)),
        Transaction(client_id=c2.id, instrument_name="Titan Company", transaction_type="BUY", quantity=500, price=2750, amount=1375000, transaction_date=today - timedelta(days=20)),
    ]
    db.add_all(c2_txns)

    c2_interactions = [
        Interaction(client_id=c2.id, interaction_type="call", summary="Discussed Goa property options. Client shortlisting 3 properties in Assagao.", interaction_date=today - timedelta(days=10)),
        Interaction(client_id=c2.id, interaction_type="meeting", summary="Quarterly review. Retirement plan on track. Discussed increasing SIP amount.", interaction_date=today - timedelta(days=40)),
    ]
    db.add_all(c2_interactions)

    # =========================================================================
    # Client 3: Rajesh Singhania — UHNI, ₹38 Cr, Moderate
    # =========================================================================
    c3 = Client(
        name="Rajesh Singhania", email="rajesh.singhania@example.com", phone="+91-98765-22222",
        dob=date(1965, 12, 5), pan="CDSPS9012C", aadhaar_last4="8901",
        address="7 Prithviraj Road, New Delhi 110011",
        segment="UHNI", risk_profile="Moderate", kyc_status="verified",
        annual_income=45000000, aum=380000000, rm_name="Vikram Sharma",
    )
    db.add(c3)
    db.flush()

    c3_holdings = [
        Holding(client_id=c3.id, instrument_name="Reliance Industries", instrument_type="Equity", quantity=8000, purchase_price=2100, current_price=2952, purchase_date=date(2023, 2, 15)),
        Holding(client_id=c3.id, instrument_name="HDFC Bank", instrument_type="Equity", quantity=10000, purchase_price=1480, current_price=1685, purchase_date=date(2023, 1, 20)),
        Holding(client_id=c3.id, instrument_name="SBI Corporate Bond Fund", instrument_type="Bond", quantity=500000, purchase_price=41, current_price=44.5, purchase_date=date(2023, 3, 10)),
        Holding(client_id=c3.id, instrument_name="UTI Nifty 50 Index Fund", instrument_type="MF", quantity=150000, purchase_price=138, current_price=168, purchase_date=date(2023, 4, 1)),
        Holding(client_id=c3.id, instrument_name="ICICI Prudential Bluechip Fund", instrument_type="MF", quantity=200000, purchase_price=74, current_price=92.5, purchase_date=date(2023, 2, 1)),
        Holding(client_id=c3.id, instrument_name="Sovereign Gold Bond 2030", instrument_type="Gold", quantity=800, purchase_price=5100, current_price=7240, purchase_date=date(2023, 5, 15)),
        Holding(client_id=c3.id, instrument_name="HDFC Flexi Cap Fund", instrument_type="MF", quantity=300000, purchase_price=33, current_price=42.8, purchase_date=date(2023, 6, 1)),
        Holding(client_id=c3.id, instrument_name="Bajaj Finance", instrument_type="Equity", quantity=4000, purchase_price=6500, current_price=7450, purchase_date=date(2023, 7, 10)),
        Holding(client_id=c3.id, instrument_name="Infosys", instrument_type="Equity", quantity=6000, purchase_price=1350, current_price=1842, purchase_date=date(2023, 3, 20)),
        Holding(client_id=c3.id, instrument_name="GreenEnergy Pvt Ltd (Unlisted)", instrument_type="Alternate", quantity=100000, purchase_price=85, current_price=125, purchase_date=date(2022, 9, 1)),
        Holding(client_id=c3.id, instrument_name="Motilal Oswal Nasdaq 100 FOF", instrument_type="MF", quantity=80000, purchase_price=26, current_price=38.2, purchase_date=date(2023, 4, 15)),
    ]
    db.add_all(c3_holdings)

    c3_goals = [
        Goal(client_id=c3.id, name="Family Trust Setup", target_amount=200000000, current_amount=380000000, target_year=2026),
        Goal(client_id=c3.id, name="Daughter's Wedding Fund", target_amount=50000000, current_amount=35000000, target_year=2025),
        Goal(client_id=c3.id, name="Philanthropic Endowment", target_amount=100000000, current_amount=20000000, target_year=2030),
    ]
    db.add_all(c3_goals)

    c3_txns = [
        Transaction(client_id=c3.id, instrument_name="HDFC Bank", transaction_type="BUY", quantity=3000, price=1480, amount=4440000, transaction_date=today - timedelta(days=160)),
        Transaction(client_id=c3.id, instrument_name="SBI Corporate Bond Fund", transaction_type="BUY", quantity=100000, price=41, amount=4100000, transaction_date=today - timedelta(days=130)),
        Transaction(client_id=c3.id, instrument_name="Sovereign Gold Bond 2030", transaction_type="BUY", quantity=200, price=5100, amount=1020000, transaction_date=today - timedelta(days=100)),
        Transaction(client_id=c3.id, instrument_name="Infosys", transaction_type="DIVIDEND", quantity=0, price=0, amount=108000, transaction_date=today - timedelta(days=80)),
        Transaction(client_id=c3.id, instrument_name="ICICI Prudential Bluechip Fund", transaction_type="SIP", quantity=13513, price=74, amount=1000000, transaction_date=today - timedelta(days=50)),
        Transaction(client_id=c3.id, instrument_name="GreenEnergy Pvt Ltd (Unlisted)", transaction_type="BUY", quantity=25000, price=105, amount=2625000, transaction_date=today - timedelta(days=25)),
    ]
    db.add_all(c3_txns)

    c3_interactions = [
        Interaction(client_id=c3.id, interaction_type="meeting", summary="Discussed family trust structure with legal team. Client wants irrevocable trust for 3 children.", interaction_date=today - timedelta(days=7)),
        Interaction(client_id=c3.id, interaction_type="call", summary="Wedding planning update. Client approved ₹50L for venue booking.", interaction_date=today - timedelta(days=30)),
        Interaction(client_id=c3.id, interaction_type="email", summary="Sent philanthropic endowment options — DAF vs private foundation comparison.", interaction_date=today - timedelta(days=55)),
    ]
    db.add_all(c3_interactions)

    # =========================================================================
    # Client 4: Kavitha Iyer — HNI, ₹3.1 Cr, Conservative
    # =========================================================================
    c4 = Client(
        name="Kavitha Iyer", email="kavitha.iyer@example.com", phone="+91-98765-33333",
        dob=date(1978, 5, 18), pan="DEKI4567D", aadhaar_last4="2345",
        address="18 Boat Club Road, Pune, Maharashtra 411001",
        segment="HNI", risk_profile="Conservative", kyc_status="verified",
        annual_income=8000000, aum=31000000, rm_name="Vikram Sharma",
    )
    db.add(c4)
    db.flush()

    c4_holdings = [
        Holding(client_id=c4.id, instrument_name="SBI Corporate Bond Fund", instrument_type="Bond", quantity=200000, purchase_price=41, current_price=44.5, purchase_date=date(2023, 4, 1)),
        Holding(client_id=c4.id, instrument_name="HDFC Bank", instrument_type="Equity", quantity=2000, purchase_price=1500, current_price=1685, purchase_date=date(2023, 5, 15)),
        Holding(client_id=c4.id, instrument_name="UTI Nifty 50 Index Fund", instrument_type="MF", quantity=30000, purchase_price=145, current_price=168, purchase_date=date(2023, 6, 1)),
        Holding(client_id=c4.id, instrument_name="ICICI Prudential Bluechip Fund", instrument_type="MF", quantity=40000, purchase_price=77, current_price=92.5, purchase_date=date(2023, 7, 1)),
        Holding(client_id=c4.id, instrument_name="Sovereign Gold Bond 2029", instrument_type="Gold", quantity=150, purchase_price=5300, current_price=7240, purchase_date=date(2023, 6, 15)),
        Holding(client_id=c4.id, instrument_name="HDFC Flexi Cap Fund", instrument_type="MF", quantity=50000, purchase_price=35.5, current_price=42.8, purchase_date=date(2023, 8, 1)),
        Holding(client_id=c4.id, instrument_name="Reliance Industries", instrument_type="Equity", quantity=800, purchase_price=2400, current_price=2952, purchase_date=date(2023, 9, 15)),
        Holding(client_id=c4.id, instrument_name="Infosys", instrument_type="Equity", quantity=1200, purchase_price=1450, current_price=1842, purchase_date=date(2023, 3, 10)),
        Holding(client_id=c4.id, instrument_name="Axis Short Term Fund", instrument_type="Bond", quantity=100000, purchase_price=25, current_price=27.2, purchase_date=date(2023, 5, 20)),
        Holding(client_id=c4.id, instrument_name="PPF Account", instrument_type="Bond", quantity=1, purchase_price=1500000, current_price=1680000, purchase_date=date(2020, 4, 1)),
    ]
    db.add_all(c4_holdings)

    c4_goals = [
        Goal(client_id=c4.id, name="Child Education Fund", target_amount=20000000, current_amount=12000000, target_year=2028),
        Goal(client_id=c4.id, name="Capital Preservation", target_amount=31000000, current_amount=31000000, target_year=2030),
    ]
    db.add_all(c4_goals)

    c4_txns = [
        Transaction(client_id=c4.id, instrument_name="SBI Corporate Bond Fund", transaction_type="SIP", quantity=12195, price=41, amount=500000, transaction_date=today - timedelta(days=140)),
        Transaction(client_id=c4.id, instrument_name="UTI Nifty 50 Index Fund", transaction_type="SIP", quantity=1724, price=145, amount=250000, transaction_date=today - timedelta(days=110)),
        Transaction(client_id=c4.id, instrument_name="HDFC Bank", transaction_type="DIVIDEND", quantity=0, price=0, amount=38000, transaction_date=today - timedelta(days=85)),
        Transaction(client_id=c4.id, instrument_name="Sovereign Gold Bond 2029", transaction_type="BUY", quantity=50, price=5300, amount=265000, transaction_date=today - timedelta(days=60)),
        Transaction(client_id=c4.id, instrument_name="ICICI Prudential Bluechip Fund", transaction_type="SIP", quantity=6493, price=77, amount=500000, transaction_date=today - timedelta(days=35)),
        Transaction(client_id=c4.id, instrument_name="Axis Short Term Fund", transaction_type="SIP", quantity=10000, price=25, amount=250000, transaction_date=today - timedelta(days=15)),
    ]
    db.add_all(c4_txns)

    c4_interactions = [
        Interaction(client_id=c4.id, interaction_type="call", summary="Reviewed education fund progress. On track. Discussed locking in FD rates before rate cut.", interaction_date=today - timedelta(days=12)),
        Interaction(client_id=c4.id, interaction_type="meeting", summary="Annual review. Client concerned about equity volatility. Reinforced long-term plan.", interaction_date=today - timedelta(days=50)),
    ]
    db.add_all(c4_interactions)

    # =========================================================================
    # Client 5: Sameer Kulkarni — Mass Affluent, ₹48 L, Moderate
    # =========================================================================
    c5 = Client(
        name="Sameer Kulkarni", email="sameer.kulkarni@example.com", phone="+91-98765-44444",
        dob=date(1992, 11, 30), pan="EFGPK7890E", aadhaar_last4="6789",
        address="203 Hiranandani Gardens, Powai, Mumbai 400076",
        segment="Mass Affluent", risk_profile="Moderate", kyc_status="verified",
        annual_income=2400000, aum=4800000, rm_name="Vikram Sharma",
    )
    db.add(c5)
    db.flush()

    c5_holdings = [
        Holding(client_id=c5.id, instrument_name="UTI Nifty 50 Index Fund", instrument_type="MF", quantity=8000, purchase_price=140, current_price=168, purchase_date=date(2023, 7, 1)),
        Holding(client_id=c5.id, instrument_name="HDFC Flexi Cap Fund", instrument_type="MF", quantity=15000, purchase_price=34, current_price=42.8, purchase_date=date(2023, 8, 1)),
        Holding(client_id=c5.id, instrument_name="ICICI Prudential Bluechip Fund", instrument_type="MF", quantity=10000, purchase_price=75, current_price=92.5, purchase_date=date(2023, 6, 15)),
        Holding(client_id=c5.id, instrument_name="SBI Corporate Bond Fund", instrument_type="Bond", quantity=20000, purchase_price=42, current_price=44.5, purchase_date=date(2023, 9, 1)),
        Holding(client_id=c5.id, instrument_name="Reliance Industries", instrument_type="Equity", quantity=200, purchase_price=2500, current_price=2952, purchase_date=date(2023, 10, 10)),
        Holding(client_id=c5.id, instrument_name="HDFC Bank", instrument_type="Equity", quantity=300, purchase_price=1550, current_price=1685, purchase_date=date(2023, 11, 1)),
        Holding(client_id=c5.id, instrument_name="Infosys", instrument_type="Equity", quantity=250, purchase_price=1500, current_price=1842, purchase_date=date(2023, 8, 20)),
        Holding(client_id=c5.id, instrument_name="Sovereign Gold Bond 2029", instrument_type="Gold", quantity=30, purchase_price=5500, current_price=7240, purchase_date=date(2023, 9, 15)),
        Holding(client_id=c5.id, instrument_name="Axis Short Term Fund", instrument_type="Bond", quantity=15000, purchase_price=25.5, current_price=27.2, purchase_date=date(2023, 10, 1)),
        Holding(client_id=c5.id, instrument_name="Motilal Oswal Nasdaq 100 FOF", instrument_type="MF", quantity=5000, purchase_price=29, current_price=38.2, purchase_date=date(2023, 7, 20)),
    ]
    db.add_all(c5_holdings)

    c5_goals = [
        Goal(client_id=c5.id, name="First Home Down Payment", target_amount=4000000, current_amount=2800000, target_year=2026),
        Goal(client_id=c5.id, name="Emergency Fund", target_amount=1200000, current_amount=900000, target_year=2025),
    ]
    db.add_all(c5_goals)

    c5_txns = [
        Transaction(client_id=c5.id, instrument_name="UTI Nifty 50 Index Fund", transaction_type="SIP", quantity=357, price=140, amount=50000, transaction_date=today - timedelta(days=150)),
        Transaction(client_id=c5.id, instrument_name="HDFC Flexi Cap Fund", transaction_type="SIP", quantity=1470, price=34, amount=50000, transaction_date=today - timedelta(days=120)),
        Transaction(client_id=c5.id, instrument_name="ICICI Prudential Bluechip Fund", transaction_type="SIP", quantity=666, price=75, amount=50000, transaction_date=today - timedelta(days=90)),
        Transaction(client_id=c5.id, instrument_name="Reliance Industries", transaction_type="BUY", quantity=100, price=2500, amount=250000, transaction_date=today - timedelta(days=60)),
        Transaction(client_id=c5.id, instrument_name="SBI Corporate Bond Fund", transaction_type="SIP", quantity=1190, price=42, amount=50000, transaction_date=today - timedelta(days=30)),
        Transaction(client_id=c5.id, instrument_name="Sovereign Gold Bond 2029", transaction_type="BUY", quantity=10, price=5500, amount=55000, transaction_date=today - timedelta(days=15)),
    ]
    db.add_all(c5_txns)

    c5_interactions = [
        Interaction(client_id=c5.id, interaction_type="call", summary="Discussed home loan pre-approval. Client targeting Navi Mumbai properties under ₹80L.", interaction_date=today - timedelta(days=8)),
        Interaction(client_id=c5.id, interaction_type="email", summary="Sent comparison of home loan rates from 5 banks.", interaction_date=today - timedelta(days=25)),
    ]
    db.add_all(c5_interactions)

    db.commit()
    db.close()
    logger.info("Database seeded with 5 clients")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_data()
    print("Seed complete!")
