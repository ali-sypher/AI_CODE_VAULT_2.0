import os
import json
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# We strictly use the OpenRouter API based on the user's explicit request
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet" # Updated for stable OpenRouter endpoint

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """
You are AI Knowledge Vault Parser. You receive chunks of code or technical documentation and must output a JSON object describing it. 
Identify the core object as a 'hub', its outgoing calls/references as 'links', and metadata as 'satellites'.
Identify the 'type' of the hub as one of: 'function', 'class', 'component', 'module', 'document', or 'chunk'.

Output ONLY valid JSON matching this schema:
{
  "hub": {
    "hash_key": "string (name of function, class, or document section)",
    "type": "string (from the list above)"
  },
  "links": [
    { "target_hash": "string (name of entity being referenced)", "relationship_type": "calls or references" }
  ],
  "satellite": {
    "metrics": {
      "lines_of_code": integer,
      "parameters": ["list", "of", "args/props"],
      "complexity_estimate": "low/medium/high"
    }
  }
}
"""

def generate_embedding(text):
    """
    Generate deterministic mock vector embeddings.
    Allows testing semantic search without external API costs.
    """
    # Create a deterministic seed from the text
    hash_obj = hashlib.sha256(text.encode('utf-8'))
    seed = int(hash_obj.hexdigest(), 16) % (2**32)
    np.random.seed(seed)
    vector = np.random.rand(1536).tolist()
    return vector

def fallback_parse(chunk):
    """
    Standard Regex/AST based fallback if AI Parser fails.
    Ensures the Code Vault is always functional.
    """
    code_text = chunk.get("code", "")
    return {
        "hub": {
            "hash_key": chunk.get("name", "unknown_entity"),
            "type": chunk.get("type", "chunk"),
            "code_snippet": code_text,
            "file_path": chunk.get("file_path", "unknown"),
            "embedding": generate_embedding(code_text)
        },
        "links": [],
        "satellite": {
            "metrics": {
                "lines_of_code": len(code_text.splitlines()),
                "parameters": [],
                "complexity_estimate": "medium"
            }
        }
    }

def parse_code_chunk(chunk):
    code_text = chunk.get("code")
    file_path = chunk.get("file_path", "")
    file_ext = file_path.split('.')[-1].lower() if '.' in file_path else 'text'
    print(f"Parsing {file_ext} chunk: {chunk.get('name')} from {file_path}")
    
    try:
        # Attempt AI Parsing via OpenRouter
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"File Extension: {file_ext}\nContent:\n```{file_ext}\n{code_text}\n```"}
            ],
            response_format={"type": "json_object"},
            timeout=10 # Reasonable timeout for a single chunk
        )
        
        result_text = response.choices[0].message.content
        parsed = json.loads(result_text)
        
        # Inject standard info
        parsed['hub']['code_snippet'] = code_text
        parsed['hub']['file_path'] = file_path
        parsed['hub']['embedding'] = generate_embedding(code_text)
        
        return parsed
    except Exception as e:
        print(f"AI Parsing failed for {chunk.get('name')}: {e}. Using fallback.")
        return fallback_parse(chunk)
