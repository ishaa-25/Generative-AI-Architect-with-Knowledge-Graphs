from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
app = FastAPI()
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
    response = requests.post("http://localhost:3030/healthcare/sparql",
                            data={"query": sparql_query},
                            headers={"Accept": "application/sparqlresults+json"})
    data = response.json()
    pairs = [(b['drug']['value'].split('#')[-1], b['mechanism']['value'].split('#')[-1])
            for b in data['results']['bindings']]
    prompt = f"Explain how {pairs[0][0]} treats arthritis by acting as a {pairs[0][1]}."
    return JSONResponse(content={"prompt": prompt})
