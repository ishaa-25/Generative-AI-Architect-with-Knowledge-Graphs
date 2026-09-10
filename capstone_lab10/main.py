import os
import faiss
import numpy as np
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from rdflib import Graph
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Autonomous Credit Fraud & AML Copilot API")

# 1. Initialize Sentence Embedder and In-Memory RDF Graph
embedder = SentenceTransformer("all-MiniLM-L6-v2")

kg = Graph()
current_dir = os.path.dirname(os.path.abspath(__file__))
ttl_filepath = os.path.join(current_dir, "ontology.ttl")
with open(ttl_filepath, "r", encoding="utf-8") as f:
  kg.parse(data=f.read(), format="turtle")

# 2. In-Memory Vector Store (Historical SAR Typologies)
historical_sars = [
    {
        "typology": "Layering / Mule Ring",
        "narrative": (
            "Multiple interrelated accounts accessing the same physical"
            " device hardware ID and rapidly hopping funds downstream to"
            " drain credit lines."
        ),
        "recommended_action": (
            "Immediate account freeze and SAR filing under Section 314(b)."
        ),
    },
    {
        "typology": "Synthetic Identity Infiltration",
        "narrative": (
            "Discrepancies in SSN issue date vs credit bureau file creation"
            " date combined with single-use burner email providers."
        ),
        "recommended_action": (
            "Escalate to manual document verification unit."
        ),
    },
    {
        "typology": "Rapid Velocity Credit Bust-Out",
        "narrative": (
            "Sudden 300% surge in max credit line utilization within 48"
            " hours at high-risk merchant categories followed by ACH bounce."
        ),
        "recommended_action": (
            "Restructure card authorization limits and revoke ACH"
            " privileges."
        ),
    },
]

sar_texts = [item["narrative"] for item in historical_sars]
sar_embeddings = embedder.encode(sar_texts)
dimension = sar_embeddings.shape[1]
vector_index = faiss.IndexFlatL2(dimension)
vector_index.add(np.array(sar_embeddings).astype("float32"))


# Schema validation
class FraudInvestigationRequest(BaseModel):
  account_id: str
  dispute_memo: str


# Step 4 Agent Roles
def planner_agent(account_id: str, dispute_memo: str) -> dict:
  """Decomposes the input query into targeted retrieval tasks."""
  formatted_account = (
      f"ex:{account_id}" if not account_id.startswith("ex:") else account_id
  )
  return {
      "target_account": formatted_account,
      "semantic_query": dispute_memo,
  }


def retriever_agent(plan: dict) -> dict:
  """Executes deterministic graph traversal and vector similarity search."""
  target_account = plan["target_account"]

  # A. Query RDF Knowledge Graph using SPARQL
  sparql_query = f"""
    PREFIX ex: <http://fintech.example.org/aml#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?originLabel ?targetAcc ?deviceLabel
    WHERE {{
        {target_account} rdfs:label ?originLabel ;
                        ex:transferredTo ?targetAcc ;
                        ex:sharesDeviceWith ?device .
        ?device rdfs:label ?deviceLabel .
    }}
    """
  graph_results = list(kg.query(sparql_query))

  if not graph_results:
    graph_context = {
        "mule_network_detected": False,
        "details": "No linked device anomalies found.",
    }
  else:
    row = graph_results[0]
    graph_context = {
        "mule_network_detected": True,
        "origin_account": str(row.originLabel),
        "hop_target": str(row.targetAcc).split("#")[-1],
        "shared_device": str(row.deviceLabel),
    }

  # B. Query FAISS Vector Store
  query_vector = embedder.encode([plan["semantic_query"]]).astype("float32")
  _, indices = vector_index.search(query_vector, k=1)
  matched_precedent = historical_sars[indices[0][0]]

  return {
      "graph_evidence": graph_context,
      "historical_precedent": matched_precedent,
  }


def summarizer_agent(plan: dict, retrieved_context: dict) -> dict:
  """Synthesizes structured context into a compliance SAR narrative."""
  evidence = retrieved_context["graph_evidence"]
  precedent = retrieved_context["historical_precedent"]

  if evidence.get("mule_network_detected"):
    sar_narrative = (
        f"CRITICAL FRAML AUDIT: Transaction alert verified for"
        f" {evidence['origin_account']}. Deterministic graph analysis"
        f" confirms shared hardware signature '{evidence['shared_device']}'"
        f" facilitating circular transfer to {evidence['hop_target']}."
        f" Matched historical typology: {precedent['typology']}."
        f" Recommendation: {precedent['recommended_action']}"
    )
    risk_level = "HIGH"
  else:
    sar_narrative = (
        f"Standard transaction alert. No structural mule network identified."
        f" Semantic precedent: {precedent['typology']}."
    )
    risk_level = "LOW"

  return {
      "suspect_account": plan["target_account"].replace("ex:", ""),
      "risk_level": risk_level,
      "sar_draft_narrative": sar_narrative,
      "retrieved_typology": precedent["typology"],
      "verified_hardware_link": evidence.get("shared_device", "None"),
  }


@app.post("/investigate-fraud")
def investigate_endpoint(request: FraudInvestigationRequest):
  plan = planner_agent(request.account_id, request.dispute_memo)
  retrieved = retriever_agent(plan)
  result = summarizer_agent(plan, retrieved)
  return JSONResponse(content=result)