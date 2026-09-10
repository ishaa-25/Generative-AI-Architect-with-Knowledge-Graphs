import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from rdflib import Graph

app = FastAPI()
# 1. Resolve path relative to this script file
CURRENT_DIR = Path(__file__).resolve().parent
TTL_PATH = CURRENT_DIR / "HealthcareAssistant.ttl"

# Fallback to parent directory if not found in current directory
if not TTL_PATH.exists():
  TTL_PATH = CURRENT_DIR.parent / "HealthcareAssistant.ttl"

# 2. Parse the Graph
g = Graph()
g.parse(str(TTL_PATH), format="turtle")
@app.get("/generate-prompt")
def get_prompt():
  sparql_query = """
    PREFIX ex: <http://www.example.org/ontology#>
    SELECT ?drug ?mechanism
    WHERE {
        ?drug ex:treats ex:Arthritis .
        ?drug ex:hasMechanism ?mechanism .
    }
    """
  results = g.query(sparql_query)

  pairs = [
      (str(row.drug).split("#")[-1], str(row.mechanism).split("#")[-1])
      for row in results
  ]

  # Guard against empty list index errors
  if not pairs:
    raise HTTPException(
        status_code=404,
        detail=(
            "No matching triples found in graph. Verify that"
            " HealthcareAssistant.ttl contains ex:treats and ex:hasMechanism"
            " triples."
        ),
    )

  prompt = (
      f"Explain how {pairs[0][0]} treats arthritis by acting as a"
      f" {pairs[0][1]}."
  )
  return JSONResponse(
      content={"prompt": prompt, "drug": pairs[0][0], "mechanism": pairs[0][1]}
  )