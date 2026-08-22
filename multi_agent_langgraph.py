import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, END

# 1. Load environment variables
load_dotenv()

# 2. Define the Graph State (Acts as shared memory across agents)
class AgentState(TypedDict):
    input: str
    planner_output: str
    retrieved_info: str
    final_output: str

# 3. Initialize LLM & Tools
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)
search = DuckDuckGoSearchRun()

# ---------------------------------------------------------
# 4. Agent Nodes (Functions)
# ---------------------------------------------------------

def planner_node(state: AgentState):
    user_input = state["input"]
    prompt = f"Convert this user request into a single concise search engine query: {user_input}"
    response = llm.invoke(prompt)
    return {"planner_output": response.content.strip()}

def retriever_node(state: AgentState):
    query = state["planner_output"]
    search_results = search.invoke(query)
    return {"retrieved_info": search_results}

def summarizer_node(state: AgentState):
    raw_info = state["retrieved_info"]
    prompt = f"Summarize the following search findings clearly for the user:\n\n{raw_info}"
    response = llm.invoke(prompt)
    return {"final_output": response.content.strip()}

# ---------------------------------------------------------
# 5. Build the LangGraph Workflow
# ---------------------------------------------------------
workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("summarizer", summarizer_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "retriever")
workflow.add_edge("retriever", "summarizer")
workflow.add_edge("summarizer", END)

app = workflow.compile()

# ---------------------------------------------------------
# 6. Execute Pipeline
# ---------------------------------------------------------
if __name__ == "__main__":
    query = "Tell me what is new about Mars exploration"
    print(f"User Request: {query}\n" + "=" * 50)
    
    result = app.invoke({"input": query})
    
    print("\n--- 📋 Planner Output (Generated Query) ---")
    print(result["planner_output"])
    
    print("\n--- 🔎 Retriever Output (Raw Search Data) ---")
    print(result["retrieved_info"][:300] + "...")
    
    print("\n--- ✍️ Summarizer Output (Final Answer) ---")
    print(result["final_output"])
