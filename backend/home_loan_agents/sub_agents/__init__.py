"""Sub-agents for Home Loan Document Verification.

Optimized: 3 combined agents instead of 6 separate ones.
- doc_quality_agent: classification + duplicate detection
- identity_income_agent: PAN/Aadhaar + salary verification
- property_eligibility_agent: property docs + loan eligibility
"""

from .doc_quality_agent import doc_quality_agent
from .identity_income_agent import identity_income_agent
from .property_eligibility_agent import property_eligibility_agent

# Keep old agents for reference but don't import them
# from .document_classifier import document_classifier_agent
# from .duplicate_detector import duplicate_detector_agent
# from .identity_verifier import identity_verifier_agent
# from .income_verifier import income_verifier_agent
# from .property_verifier import property_verifier_agent
# from .eligibility_assessor import eligibility_assessor_agent

__all__ = [
    "doc_quality_agent",
    "identity_income_agent",
    "property_eligibility_agent",
]
