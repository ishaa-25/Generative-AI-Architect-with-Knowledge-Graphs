import pandas as pd
from rdflib import Graph, Literal, RDF, Namespace, URIRef, XSD

# Load CSV
df = pd.read_csv("products.csv")

g = Graph()
EX = Namespace("http://example.org/products#")
g.bind("ex", EX)

for _, row in df.iterrows():
    prod_uri = URIRef(EX + str(row["id"]).strip())
    g.add((prod_uri, RDF.type, EX.Product))
    g.add((prod_uri, EX.name, Literal(str(row["name"]).strip())))
    g.add((prod_uri, EX.category, Literal(str(row["category"]).strip())))
    g.add((prod_uri, EX.price, Literal(row["price"], datatype=XSD.decimal)))

# Save as Turtle file
g.serialize("products.ttl", format="turtle")
print("✅ Successfully generated products.ttl!")
