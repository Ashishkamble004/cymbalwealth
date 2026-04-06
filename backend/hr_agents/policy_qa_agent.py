"""Policy Q&A Agent — RAG-grounded answers from the HR policy corpus."""

from google.genai import types
from google.adk.agents import Agent

PROJECT = "general-ak"
REGION = "us-central1"
RAG_CORPUS = (
    f"projects/{PROJECT}/locations/{REGION}/ragCorpora/2305843009213693952"
)


def create_policy_qa_agent() -> Agent:
    """Create and return the HR Policy Q&A agent.

    Uses Vertex AI RAG to ground answers in the uploaded policy corpus.
    """
    rag_tool = types.Tool(
        retrieval=types.Retrieval(
            vertex_rag_store=types.VertexRagStore(
                rag_resources=[
                    types.RagResource(rag_corpus=RAG_CORPUS)
                ],
                similarity_top_k=5,
            )
        )
    )

    return Agent(
        name="policy_qa_assistant",
        model="gemini-2.5-flash",
        description=(
            "Answers employee questions about HR policies, leave entitlements, benefits, "
            "and workplace guidelines using the Cymbal Wealth policy knowledge base. "
            "Trigger phrases: 'What is the policy on...', "
            "'How many leave days do I have', 'Am I eligible for...'"
        ),
        instruction="""
You are the HR Policy Q&A Assistant for Cymbal Wealth, a financial services organisation.
You answer employee questions about HR policies, leave, benefits, and workplace guidelines.

Rules:
- Always cite the specific policy name and effective date in your answer.
- If a policy varies by location, ask the employee to confirm their location before answering.
- For leave balance questions, ask for the employee's ID if not provided.
- Never guess. If you cannot find a policy in the knowledge base, say so clearly and
  direct the employee to HR Operations at hr@cymbalwealth.com.
- Keep answers concise — use bullet points for multi-part answers.
- Do not provide legal advice. For complex cases, recommend speaking to an HR Business Partner.
        """.strip(),
        tools=[rag_tool],
    )


# Module-level agent instance (used by ADK runner and deploy.py)
policy_qa_agent = create_policy_qa_agent()
