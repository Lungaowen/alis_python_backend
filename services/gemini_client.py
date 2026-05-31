import json
import gc
import logging
import httpx
from config import config

logger = logging.getLogger(__name__)
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

def analyze_document(document_type: str, jurisdiction: str, extracted_text: str) -> dict:
    """
    Analyzes a legal document using Groq's accelerated infrastructure.
    
    Optimized for Groq's OpenAI-compatible chat completions endpoint:
    - Bypasses system role restriction by merging instructions into a user prompt.
    - Sets stable reasoning temperature parameters (0.6).
    - Requests a JSON object response when the selected model supports it.
    - Strict garbage collection to keep background worker execution under 100MB.
    """
    
    # Core legal expertise parameters
    prompt_system = (
        "You are a legal compliance expert specialising in South African law including the "
        "Consumer Protection Act (CPA), Basic Conditions of Employment Act (BCEA), "
        "Labour Relations Act (LRA), National Credit Act (NCA), and POPIA. "
        "Analyse the provided document text and return ONLY a valid JSON object. "
        "Do not include any introductory text, markdown formatting blocks (such as ```json), "
        "or structural explanations outside of the raw JSON."
    )
    
    # Schema configuration string
    schema_instructions = f"""
    Document type: {document_type}
    Jurisdiction: {jurisdiction}
    
    Document text:
    {extracted_text}
    
    You must analyze the document above and output a valid JSON object adhering strictly to this structural blueprint:
    {{
      "riskLevel": "HIGH|MEDIUM|LOW",
      "complianceScore": 0-100,
      "overallExplanation": "string summary of legal compliance status",
      "overallRecommendation": "string outlining clear actionable next steps",
      "clauses": [
        {{
          "clauseNumber": 1,
          "text": "exact matching clause text string from the document",
          "riskLevel": "HIGH|MEDIUM|LOW",
          "riskReason": "detailed explanation of why this clause risks non-compliance",
          "lawReference": "specific statutory reference, e.g., BCEA s37 or POPIA s11",
          "recommendation": "re-drafting guidance to mitigate the identified risk",
          "highlight": true,
          "pageNumber": null
        }}
      ],
      "riskBreakdown": {{
        "high": 0,
        "medium": 0,
        "low": 0
      }},
      "lawsApplicable": ["BCEA", "LRA", "CPA", "POPIA", "NCA"],
      "modelVersion": "{config.GROQ_MODEL}",
      "processedAt": "2026-05-30T14:42:39Z"
    }}
    """
    
    # CRITICAL GROQ COMPLIANCE: Merge system and user roles into a single user message block
    combined_content = f"Instructions:\n{prompt_system}\n\nExecution Task:\n{schema_instructions}"
    
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [
            {
                "role": "user", 
                "content": combined_content
            }
        ],
        # Activates JSON validation mode (requires the word "json" to be present in the prompt text)
        "response_format": {"type": "json_object"},
        # Stable low-variance generation for compliance reports
        "temperature": 0.6
    }
    
    for attempt in range(2):
        try:
            # Localized HTTP client manager ensures connection sockets close immediately after use
            with httpx.Client() as client:
                response = client.post(
                    GROQ_CHAT_COMPLETIONS_URL,
                    json=payload,
                    headers=headers,
                    timeout=120.0
                )
                response.raise_for_status()
                response_json = response.json()
                
                # Unpack content payload block
                raw_content = response_json['choices'][0]['message']['content']
                result = json.loads(raw_content)
                
                # Manual memory deallocation to enforce strict resource thresholds
                del response
                del response_json
                del raw_content
                gc.collect()
                
                return result
                
        except httpx.HTTPStatusError as e:
            response_body = e.response.text[:1000] if e.response is not None else ""
            logger.exception(
                "Groq request attempt %s failed with status %s: %s",
                attempt + 1,
                e.response.status_code if e.response is not None else "unknown",
                response_body
            )
            if attempt == 1:
                raise RuntimeError(
                    f"Groq Processing Pipeline Failed: {e}. Response body: {response_body}"
                ) from e
        except Exception as e:
            logger.exception("Groq request attempt %s failed", attempt + 1)
            if attempt == 1:
                raise RuntimeError(f"Groq Processing Pipeline Failed: {str(e)}") from e


# Quick local diagnostic script execution check
if __name__ == "__main__":
    # Mocking standard inputs for a quick execution check
    test_text = "The Employee shall work 60 hours per week without overtime compensation."
    print("Initiating local Groq pipeline structural test...")
    try:
        mock_analysis = analyze_document("Employment Contract", "South Africa", test_text)
        print("Success! Parsed Pipeline Payload:")
        print(json.dumps(mock_analysis, indent=2))
    except Exception as failure:
        print(f"Execution Error Encountered: {failure}")
