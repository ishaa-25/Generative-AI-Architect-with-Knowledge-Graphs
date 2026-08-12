from rdflib import Graph, Literal, RDF, Namespace, URIRef
import json
g = Graph()
EX = Namespace("http://example.org/employees#")
g.bind("ex", EX)
with open("employees.json") as f:
    data = json.load(f)
for item in data:
    emp_uri = URIRef(EX + item["id"])
    g.add((emp_uri, RDF.type, EX.Employee))
    g.add((emp_uri, EX.name, Literal(item["name"])))
    g.add((emp_uri, EX.role, Literal(item["role"])))
    g.add((emp_uri, EX.department, Literal(item["department"])))
g.serialize("employees.ttl", format="turtle")