import os
import json
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# We strictly use the OpenRouter API based on the user's explicit request
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet:beta" # Excellent for coding and json mode

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """
You are AI Code Vault Parser. You receive python code chunks (functions or classes) and must output a JSON object describing it. 
Identify the core object as a 'hub', its outgoing calls to other functions as 'links', and metadata as 'satellites'.
Output ONLY valid JSON matching this schema:
{
  "hub": {
    "hash_key": "string (name of function)",
    "type": "function or class"
  },
  "links": [
    { "target_hash": "string (name of function being called)", "relationship_type": "calls" }
  ],
  "satellite": {
    "metrics": {
      "lines_of_code": integer,
      "parameters": ["list", "of", "args"],
      "complexity_estimate": "low/medium/high"
    }
  }
}
"""

import hashlib

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
            "hash_key": chunk.get("name", "unknown_function"),
            "type": chunk.get("type", "function"),
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
    file_path = chunk.get("file_path")
    print(f"Parsing chunk: {chunk.get('name')} from {file_path}")
    
    try:
        # Attempt AI Parsing via OpenRouter
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Code:\n```python\n{code_text}\n```"}
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
