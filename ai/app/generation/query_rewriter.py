import logging
from typing import Optional

from app.generation.llm import get_llm_provider

logger = logging.getLogger(__name__)

def rewrite_query(query: str, history: Optional[list[dict[str, str]]] = None) -> str:
    """
    Rewrite the user query to be self-contained based on conversation history.
    If history is empty or irrelevant, returns the original query.
    """
    if not history:
        return query

    # Use only the last few turns to keep it focused
    recent_history = history[-4:]
    
    # Format history for the prompt
    history_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_history])
    
    prompt = f"""
Given the conversation history and the latest user request, rewrite the latest request to be a standalone sentence that fully captures the context (e.g., resolving "it", "he", "that", or implicit references).
If the request is already self-contained or doesn't need rewriting, return it logically unchanged.
DO NOT answer the question. ONLY return the rewritten query.

Conversation History:
{history_text}

Latest Request: {query}

Rewritten Request:
""".strip()

    try:
        llm = get_llm_provider()
        rewritten = llm.generate(
            prompt=prompt,
            system_prompt="You are a query rewriting assistant. Your job is to resolve pronouns and context. Output ONLY the rewritten text.",
            temperature=0.0,
            max_tokens=200
        )
        
        rewritten_clean = rewritten.strip().strip('"').strip("'")
        
        # Log if it changed significantly
        if rewritten_clean.lower() != query.lower():
            logger.info(f"Query Rewritten: '{query}' -> '{rewritten_clean}'")
            
        return rewritten_clean

    except Exception as e:
        logger.error(f"Error in query rewriting: {e}")
        return query
