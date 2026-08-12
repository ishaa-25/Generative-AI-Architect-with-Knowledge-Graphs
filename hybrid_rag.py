import os
import numpy as np
import faiss
from rdflib import Graph, Literal, Namespace, RDF
from datasets import load_dataset
from groq import Groq
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------
# 1. Initialize Clients & Local Embedding Model
# ---------------------------------------------------------
# Groq handles LLM text generation for free
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Local open-source embedding model (No API key needed, runs on CPU)
print("Loading local embedding model (all-MiniLM-L6-v2)...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def get_embedding(text):
    """Generates 384-dim vector embeddings locally using HuggingFace."""
    return embed_model.encode(text).tolist()


# ---------------------------------------------------------
# 2. Load Sample Knowledge Data (Healthcare Focus)
# ---------------------------------------------------------
print("Loading healthcare dataset...")

sample_docs = [
    "The US healthcare system provides benefits such as Medicare for seniors and Medicaid for low-income families.",
    "Health insurance in the US covers essential benefits including preventive care, emergency services, and prescription drugs.",
    "Employer-sponsored health plans in the United States often cover dental, vision, and preventive healthcare services.",
    "The European Union offers universal healthcare coverage managed by public health organizations across member states.",
    "Financial banking institutions in the US are regulated by the Federal Reserve and the Consumer Financial Protection Bureau."
]

# ---------------------------------------------------------
# 3. Build RDF Knowledge Graph
# ---------------------------------------------------------
print("Building RDF Graph...")
g = Graph()
EX = Namespace("http://example.org/")

# Explicitly link Doc 0 and Doc 1 as US Healthcare policies
g.add((EX["Doc0"], RDF.type, EX["Policy"]))
g.add((EX["Doc0"], EX["category"], Literal("Healthcare")))
g.add((EX["Doc0"], EX["region"], Literal("US")))
g.add((EX["Doc0"], EX["text"], Literal(sample_docs[0])))

g.add((EX["Doc1"], RDF.type, EX["Policy"]))
g.add((EX["Doc1"], EX["category"], Literal("Healthcare")))
g.add((EX["Doc1"], EX["region"], Literal("US")))
g.add((EX["Doc1"], EX["text"], Literal(sample_docs[1])))

g.serialize(destination="knowledge.ttl", format="turtle")
# ---------------------------------------------------------
# 4. Generate Embeddings & Index with FAISS
# ---------------------------------------------------------
print("Embedding documents locally...")
embeddings = [get_embedding(d) for d in sample_docs]

# all-MiniLM-L6-v2 produces 384-dimensional vectors
dimension = 384
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings).astype('float32'))

# ---------------------------------------------------------
# 5. Index with Pinecone (Metadata-Aware Retrieval)
# ---------------------------------------------------------
index_name = "rag-hybrid-demo"

# Create index if it doesn't exist
existing_indexes = [i.name for i in pc.list_indexes()]
if index_name not in existing_indexes:
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

pc_index = pc.Index(index_name)

# Upsert items with metadata
vectors_to_upsert = [
    {
        "id": f"doc_{i}",
        "values": embeddings[i],
        "metadata": {
            "category": "Healthcare" if i % 2 == 0 else "Finance",
            "region": "US" if i % 2 == 0 else "EU",
            "text": sample_docs[i]
        }
    }
    for i in range(len(sample_docs))
]
pc_index.upsert(vectors=vectors_to_upsert)

# ---------------------------------------------------------
# 6. Hybrid Query Pipeline
# ---------------------------------------------------------
user_query = "What are the healthcare benefits in the US?"
query_embedding = get_embedding(user_query)

# A. FAISS Vector Search (Semantic Similarity)
D, I = index.search(np.array([query_embedding]).astype('float32'), k=2)
top_faiss_docs = [sample_docs[i] for i in I[0]]

# B. Pinecone Filtered Search (Metadata + Vector)
pinecone_results = pc_index.query(
    vector=query_embedding,
    top_k=2,
    include_metadata=True,
    filter={"category": {"$eq": "Healthcare"}, "region": {"$eq": "US"}}
)
top_pinecone_docs = [match["metadata"]["text"] for match in pinecone_results["matches"]]

# C. SPARQL Graph Query (Structured Filtering)
sparql_query = """
PREFIX ex: <http://example.org/>
SELECT ?text WHERE {
    ?doc ex:category "Healthcare" ;
         ex:region "US" ;
         ex:text ?text .
}
"""
graph_results = g.query(sparql_query)
graph_texts = [str(r["text"]) for r in graph_results]

# ---------------------------------------------------------
# 7. Prompt Assembly & Generation via Groq API
# ---------------------------------------------------------
retrieved_context = list(set(top_faiss_docs + top_pinecone_docs + graph_texts))
combined_context_text = "\n---\n".join(retrieved_context)

final_prompt = f"""You are a helpful assistant. Answer the question using ONLY the provided context below.

Context:
{combined_context_text}

Question: {user_query}
Answer:"""

print("\nSending context to Groq API...")
response = groq_client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": final_prompt}]
)

print("\n================ FINAL RESPONSE ================")
print(response.choices[0].message.content)