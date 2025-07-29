# main.py
import os
import json
from typing import TypedDict, List, Optional

# Json conversion service
import lc_swft_to_json

from logger_config import logger
from prohibitions_handler import call_baoe_service
# langchain libraries
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.outputs import Generation
from langchain_ollama import ChatOllama , OllamaLLM

from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool

# Too for Json Conversion

@tool
def convert_to_json(swift_text: str) -> dict:
    """Converts a SWIFT MT 700 text to a JSON object."""

    print("--- Running Convert_to_Json Tool ---")

    lc_json = lc_swft_to_json.process_input(swift_text)
    logger.info(f" ########     JSON : \n {lc_json }")
    return lc_json


def identify_prohibitions(context: str , catgory:str) -> str:
    """External service to check for boycott and sanction clauses."""
    
    response  = call_baoe_service(context,catgory)

    if response:
        return response
    else:
        print(f"--- Checking for {catgory} clauses  ")
        return "No {catgory} clauses identified."


def evaluate_related_to_dns(goods_name: str) -> str:
    """External service to evaluate if goods are related to Dual-Use/Sensitive items."""
    print(f"--- Evaluating DNS for: {goods_name} ---")
    dns_prompt = "Goods Name : {goods_name} . Do a detailed analysis of the above Goods name with valid  sources to determine if it related to  Military , Non-military or Dual use type of Goods. Give a short description of the goods (prioritising military and dual use) in about 60-80 words.List top 3 primary uses ('top_uses') , Do not add any additional description. Generate a valid JSON with fields:  'is_related_to_defense': Boolean(true/false), 'usage_type': (Military/Dual Use/Non-Military) 'description': '' for the above goods name. Do Not generate any Explanation."
    template_dns = PromptTemplate(input_variables=["goods_name"], template=dns_prompt)
 #Create a non-streaming Ollama LLM instance
    llm_ollama = OllamaLLM(
        model="phi4:14b",
        base_url="http://ollama-service-v3.v-sharp.svc.cluster.local:11434",
        temperature=0.2,
        streaming=False  # 🔒 ensures response is complete, not streamed
    )


    chain = template_dns | llm_ollama | StrOutputParser()
    generated_response = chain.invoke({"goods_name": goods_name})

    print(f"GENERATED MISTRAL RESPONSE DNS : {generated_response}")
    if generated_response:
        return filter_response(generated_response, "{", "}")
    
    return "{}"

def filter_response(raw_response_json, startch, endch):
    raw_response_json = raw_response_json.strip()
    try:
        start_ind = raw_response_json.index(startch)
        end_ind = raw_response_json.rfind(endch)
        return raw_response_json[start_ind:end_ind + 1]
    except ValueError:
        return "{}"


# Definig Agent State
class AgentState(TypedDict):
    """
    Represents the state of our multi-agent system.
    Optional[...] allows the state to be initialized with None.
    """
    input_swift_text: str
    lc_json_data: Optional[dict]
    prohibition_results: Optional[List[str]]
    goods_details: Optional[dict]
    dns_result: Optional[str]


def json_conversion_agent(state: AgentState) -> dict:
    """Converts the input SWIFT text to JSON."""
    print("\n--- AGENT: JSON Conversion ---")
    swift_text = state["input_swift_text"]
    lc_json = convert_to_json.invoke({"swift_text": swift_text})
    return {"lc_json_data": lc_json}


def prohibition_identification_agent(state: AgentState) -> dict:
    """Identifies boycott and sanction risks."""
    print("\n--- AGENT: Prohibition Identification ---")
    lc_data = state["lc_json_data"]

    context_text = lc_data["LCDocumentRequired"] + " \n\n" + lc_data["LCAdditionalCondition"]

    boycott_result = identify_prohibitions(lc_data , "boycott")
    sanction_result = identify_prohibitions(lc_data , "sanction")
    return {"prohibition_results": [boycott_result, sanction_result]}

def goods_details_extraction_agent(state: AgentState) -> dict:
    """Extracts goods details using an LLM."""
    print("\n--- AGENT: Goods Details Extraction ---")
    lc_data = state["lc_json_data"]
    goods_description = lc_data["LCDescriptionOfGoods"]
    llm_ollama = OllamaLLM(
        model="phi4:14b",
        base_url="http://ollama-service-v3.v-sharp.svc.cluster.local:11434",
        temperature=0.2,
        streaming=False  # 🔒 ensures response is complete, not streamed
    )
    prompt = PromptTemplate(
        template='''From the following goods description, extract the goods name, quantity, and unit price.
        Provide the output in a clean JSON format with keys: "goods_name", "quantity", "unit_price".
        Description: "{description}"
        JSON Output:''',
        input_variables=["description"],
    )
    chain = prompt | llm_ollama | StrOutputParser()
    response = chain.invoke({"description": goods_description})
    response = filter_response(response,"{","}")
    print(f"GOODS DESCRIPTION ###: {response}")
    try:
        extracted_json = json.loads(response.strip())
        return {"goods_details": extracted_json}
    except json.JSONDecodeError:
        print("Error: Failed to parse LLM output into JSON.")
        return {"goods_details": {"error": "Failed to parse LLM output."}}

def dns_evaluation_agent(state: AgentState) -> dict:
    """Evaluates if the goods are related to DNS."""
    print("\n--- AGENT: DNS Evaluation ---")
    goods_details = state["goods_details"]
    if goods_details and "goods_name" in goods_details:
        dns_result = evaluate_related_to_dns(goods_details["goods_name"])
        return {"dns_result": dns_result}
    return {"dns_result": "Could not perform DNS check; goods name not found."}



#supervisor_llm = ChatMistralAI(model="mistral-large-latest", temperature=0.3)
# Supervisor LLM 
supervisor_llm = OllamaLLM(
        model="phi4:14b",
        base_url="http://ollama-service-v3.v-sharp.svc.cluster.local:11434",
        temperature=0.2,
        streaming=False  # 🔒 ensures response is complete, not streamed
    )
#supervisor_llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

# Supervisor Prompt
supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are a supervisor for a multi-agent system that processes Letters of Credit (LCs).
     Your role is to determine the next agent to run based on the current state.
     The available agents are: JsonConversionAgent, ProhibitionIdentificationAgent, GoodsDetailsExtractionAgent, DnsEvaluationAgent.

     Workflow rules:
     - If 'lc_json_data' is not present, the first step is 'JsonConversionAgent'.
     - If 'lc_json_data' is present but 'prohibition_results' is not, run 'ProhibitionIdentificationAgent'.
     - If 'prohibition_results' is present but 'goods_details' is not, run 'GoodsDetailsExtractionAgent'.
     - If 'goods_details' is present but 'dns_result' is not, run 'DnsEvaluationAgent'.
     - If 'dns_result' is present, the workflow is complete.

     Current State:
     {current_state}

     Respond with ONLY the name of the next agent to run. If the workflow is complete, respond with "END".
     Your response must be one of: JsonConversionAgent, ProhibitionIdentificationAgent, GoodsDetailsExtractionAgent, DnsEvaluationAgent, END."""),
])

# Super visor router
def supervisor_router(state: AgentState) -> str:
    """This is the central router that directs the workflow using an LLM."""
    print("\n--- SUPERVISOR: Routing decision ---")

    # Check for terminal conditions first to avoid unnecessary LLM calls
    if (state.get("goods_details") or {}).get("error"):
        print("Supervisor: Error detected in goods extraction. Halting execution.")
        return "END"
    if state.get("dns_result"):
        print("Supervisor: All steps complete. Finishing workflow.")
        return "END"

    # Format the current state for the LLM
    current_state_str = json.dumps(state, indent=2, default=str)
    chain = supervisor_prompt | supervisor_llm | StrOutputParser()
    llm_decision = chain.invoke({"current_state": current_state_str})
    next_node = llm_decision.strip()

    print(f"Supervisor LLM decision: '{next_node}'")

    valid_nodes = ["JsonConversionAgent", "ProhibitionIdentificationAgent", "GoodsDetailsExtractionAgent", "DnsEvaluationAgent", "END"]
    if next_node not in valid_nodes:
        print(f" LLM returned an invalid node name: '{next_node}'. Defaulting to END.")
        return "END"
    return next_node

# --- 5. Graph Definition and Execution ---

def get_workflow():
    workflow = StateGraph(AgentState)

    # Add all the nodes 
    
    workflow.add_node("ProhibitionIdentificationAgent", prohibition_identification_agent)
    workflow.add_node("GoodsDetailsExtractionAgent", goods_details_extraction_agent)
    workflow.add_node("DnsEvaluationAgent", dns_evaluation_agent)
    workflow.add_node("JsonConversionAgent", json_conversion_agent)

    # Define the mapping from the supervisor's decision to the node to run.
    members = ["JsonConversionAgent", "ProhibitionIdentificationAgent", "GoodsDetailsExtractionAgent", "DnsEvaluationAgent"]
    path_map = {member: member for member in members}
    path_map["END"] = END

    # Set entry point to the supervisor router. It decides the first node.
    workflow.set_conditional_entry_point(supervisor_router, path_map)

    # After run, we loop back to the supervisor to decide the next step.
    workflow.add_conditional_edges("JsonConversionAgent", supervisor_router, path_map)
    workflow.add_conditional_edges("ProhibitionIdentificationAgent", supervisor_router, path_map)
    workflow.add_conditional_edges("GoodsDetailsExtractionAgent", supervisor_router, path_map)
    workflow.add_conditional_edges("DnsEvaluationAgent", supervisor_router, path_map)
    
    # Compile the graph
    return workflow.compile()


if __name__ == "__main__":

    sample_swift_input = ""
    sample_lc_file = os.path.join("resources", "sample_lc.txt")
    try:
        with open(sample_lc_file, "r") as f:
            sample_swift_input = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{sample_lc_file}' was not found.")
        exit()
    
    initial_state = {
        "input_swift_text": sample_swift_input,
        "lc_json_data": None,
        "prohibition_results": None,
        "goods_details": None,
        "dns_result": None,
    }

    app = get_workflow()

    # Generate a visual representation of the graph
    try:
        png_data = app.get_graph(xray=True).draw_mermaid_png()
        with open("supervised_llm_graph.png", "wb") as f:
            f.write(png_data)
        print("\nGraph visualization saved to supervised_llm_graph.png")
    except Exception as e:
        print(f"\nCould not create graph visualization: {e}")

    print("\n--- STARTING WORKFLOW ---")
    final_state = app.invoke(initial_state)

    print("\n\n--- FINAL STATE ---")
    print(json.dumps(final_state, indent=2))
