"""Policy Q&A Agent — RAG-grounded answers from the HR policy corpus."""

import vertexai
from vertexai.preview import rag
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

PROJECT = "general-ak"
REGION = "us-central1"
RAG_CORPUS = f"projects/{PROJECT}/locations/{REGION}/ragCorpora/2305843009213693952"

vertexai.init(project=PROJECT, location=REGION)


def query_hr_policy(question: str) -> str:
    """Search the HR policy knowledge base for answers to employee questions.

    Args:
        question: The HR policy question to answer.

    Returns:
        Relevant policy excerpts from the knowledge base.
    """
    try:
        response = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=RAG_CORPUS)],
            text=question,
            similarity_top_k=5,
        )
        chunks = []
        for ctx in response.contexts.contexts:
            source = getattr(ctx, "source_uri", "HR Policy")
            chunks.append(f"[Source: {source}]\n{ctx.text}")
        return "\n\n---\n\n".join(chunks) if chunks else "No relevant policy found."
    except Exception as e:
        return f"Policy lookup error: {e}"


def create_policy_qa_agent() -> Agent:
    """Create and return the HR Policy Q&A agent."""
    return Agent(
        name="policy_qa_assistant",
        model="gemini-2.5-flash",
        description=(
            "Answers employee questions about HR policies, leave entitlements, benefits, "
            "and workplace guidelines using the Cymbal Wealth policy knowledge base."
        ),
        instruction="""
You are the HR Policy Q&A Assistant for Cymbal Wealth, a financial services organisation.
You answer employee questions about HR policies, leave, benefits, and workplace guidelines.

Always use the query_hr_policy tool to retrieve relevant policy before answering.

Rules:
- Always cite the specific policy name and effective date in your answer.
- If a policy varies by location, ask the employee to confirm their location before answering.
- Never guess. If you cannot find a policy in the knowledge base, say so clearly and
  direct the employee to HR Operations at hr@cymbalwealth.com.
- Keep answers concise — use bullet points for multi-part answers.
- Do not provide legal advice. For complex cases, recommend speaking to an HR Business Partner.
        """.strip(),
        tools=[FunctionTool(query_hr_policy)],
    )


# Module-level agent instance (used by ADK runner and deploy.py)
policy_qa_agent = create_policy_qa_agent()
