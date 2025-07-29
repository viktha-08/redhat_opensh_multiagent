
import os

# Json conversion service
import lc_swft_to_json

import json
from logger_config import logger

# langchain libraries
from langchain_core.messages.ai import AIMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_ollama import ChatOllama , OllamaLLM
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
import requests

def call_baoe_service(lc_json,category):
    url = ""
    if "boycott" == category.lower():
        url = "http://tf-boycott-service-v-sharp.apps.clusterocpvirtoci.ocpociibm.com/api/boycott/evaluate"
    else:
        url = "http://tf-sanction-service-v-sharp.apps.clusterocpvirtoci.ocpociibm.com/api/boycott/evaluate"

    # Headers (you can add Content-Type, Authorization, etc.)
    headers = {
        "Content-Type": "application/json"
    }

    # Make the POST request
    response = requests.post(
        url,
        json=lc_json,
        headers=headers)
    
    print(response)
    
    return response


def tag_prohibitions(p_context:str,category:str="NA"):
     #Creare a blank dictionary
    logger.info("====== run_prompt - START")

    generic_template = ""
    complete_prompt:PromptTemplate = None
    p_txt = "Question: What are the prohibitions related to international trade finance that are mentioned in provided text?  . \n List all the prohibitions one by one without repeating and caegorize the same as 'Boycott', 'Sanction' or 'Others'. \n Return  response as a valid structured JSON Only with 'category' and 'prohibition_text' (WITHOUT ANY CHANGES TO ORIGINAL TEXT OR ANY SPELLING CORRECTIONS) for each prohibition. DO NOT ADD ANY OTHER DETAILS OF YOUR OWN. In case of no prohibitions are found return blank response.\n"
 
    generic_template = """ You are an expert Trade Finance Analyst.Handle any typos in text. Answer below question based on the provided context :\n\n  {prompt_context} .\n\n  {prompt_txt}\n \n . Return response as JSON."""
    template_dns = PromptTemplate( input_variables=["prompt_context","prompt_txt"], template = generic_template)
    complete_prompt = template_dns.format(prompt_context=p_context,prompt_txt=p_txt)

    llm_ollama = OllamaLLM(
        model="phi4:14b",
        base_url="http://ollama-service-v3.v-sharp.svc.cluster.local:11434/api/generate",
        temperature=0.2,
        streaming=False  # 🔒 ensures response is complete, not streamed
    )
    

    logger.info(complete_prompt)
        
    generated_response = llm_ollama.invoke(complete_prompt)
    logger.info(f" LLM Response : type(generated_response) ")
    logger.info(f" LLM Response TYPE : {type(generated_response)} ")

    if isinstance(generated_response , AIMessage):
        # Convert to a Python dictionary
        generated_response = generated_response.model_dump_json(indent=4)
        #print(generated_response)


    prohibitions = ["sanction","boycott"]
    category = category.lower()

    if generated_response:
        if category in prohibitions:
            print( " In prohibitions ")
            response_json = filter_response(generated_response,"[", "]")
            dict_ptext = add_to_list(response_json,category)
            response_j1 = dict_ptext
        else: 
            response_json = filter_response(generated_response,"{", "}")
            response_j1  = json.loads(response_json)

       
        logger.debug(f" Json loaded Type { type(response_j1)} ")

        response_json  = response_j1
        #print(f" Formatted JSON : {response_json}")   
        response_json = json.dumps(response_json,indent=4)    
        
    return response_json

def add_to_list(json_text:json,category:str):
    #json_text = """[{"category": "Boycott", "prohibition_text": "SHIPMENT AND TRANSHIPMENT ON ISRAELI FLAG VESSEL / AIR CRAFT, SEA PORTS / AIRPORT IS NOT ALLOWED AND A CERTIFICATE ISSUED BY THE SHIPPING COMPANY OR THEIR AUTHORISE AGENT TO THIS EFFECT MUST ACCOMPANY THE ORIGINAL DOCUMENTS"}, {"category": "Boycott", "prohibition_text": "SHIPMENT THROUGH ISRAELI FLAG VESSEL IS PROHIBITED"}, {"category": "Sanction", "prohibition_text": "IBM INDIA BANK COMPLIES WITH THE INTERNATIONAL SANCTION LAWS, RESOLUTIONS AND REGULATIONS ISSUED BY THE EUROPEAN UNION, THE UNITED NATIONS AND THE UNITED STATES OF AMERICA (AS WELL AS LOCAL LAWS AND REGULATIONS GOVERNING THE ISSUING BANK). IT IS BANK POLICY TO UNDERTAKE NO OBLIGATION, UNLESS IBM INDIA BANK HAS PROVIDED ITS EXPLICIT APPROVAL PRIOR TO COMMENCEMENT OF SUCH TRANSACTION, TO MAKE ANY PAYMENT UNDER, OR OTHERWISE TO IMPLEMENT, THIS LETTER OF CREDIT (INCLUDING BUT NOT LIMITED TO PROCESSING DOCUMENTS OR ADVISING THE LETTER OF CREDIT), IF THERE IS INVOLVEMENT BY ANY PERSON, ENTITY OR BODY LISTED IN THE EU, UN, USA OR LOCAL SANCTIONS LISTS GOVERNING THE ISSUING BANK, OR ANY INVOLVEMENT BY OR NEXUS WITH CUBA, SUDAN, IRAN, NORTH KOREA OR MYANMAR, WHATSOEVER."}, {"category": "Others", "prohibition_text": "THIRD PARTY DOCUMENTS ARE NOT ALLOWED"}]"""

    #print(f" add to list : {json_text}")

    prohibitions = ["sanction","boycott"]
    response_j = json.loads(json_text)
    #print(f" ######################################### Response JSON :  {response_j}")
    list_ptext = []
    dict_p_text = {}
    if category in prohibitions:
        response_json = [record for record in response_j if record["category"].lower() == category ] 
        for entry in response_json:
            print(f"entry :  {entry}")
            list_ptext.append(entry["prohibition_text"])
        dict_p_text["category"]  = category
        dict_p_text["prohibition_text"] = list_ptext



    #print(f"Returning {dict_p_text}")

    return dict_p_text

def run_prompt(p_txt:str,p_context:str,category:str="NA"):
     #Creare a blank dictionary
    logger.info("====== run_prompt - START")
    blank_dict = '{}'

   
    generic_template = ""
    complete_prompt:PromptTemplate = None
 
    generic_template = """ You are an expert Trade Finance Analyst.Handle any typos in text. Answer below question based on the provided context :\n\n  {prompt_context} .\n\n  {prompt_txt}\n \n . Return response as JSON."""
    template_dns = PromptTemplate( input_variables=["prompt_context","prompt_txt"], template = generic_template)
    complete_prompt = template_dns.format(prompt_context=p_context,prompt_txt=p_txt)

    logger.info(complete_prompt)

    llm_ollama = ChatOllama(
        model="phi4:14b",
        base_url="http://ollama-service-v3.v-sharp.svc.cluster.local:11434",
        temperature=0.2,
        streaming=False  # 🔒 ensures response is complete, not streamed    
    )
        
    generated_response = llm_ollama.invoke(complete_prompt)
    logger.info(f" LLM Response : {generated_response} ")

    prohibitions = ["sanction","boycott"]
    category = category.lower()

    if generated_response:
        if category in prohibitions:
            response_json = filter_response(generated_response,"[", "]")
            cleaned = response_json.encode('utf-8').decode('unicode_escape')  # unescape the \n and \" etc.
            #parsed = json.loads(cleaned)
            dict_ptext = add_to_list(cleaned,category)
            response_j1 = dict_ptext
        else: 
            response_json = filter_response(generated_response,"{", "}")
            cleaned = response_json.encode('utf-8').decode('unicode_escape')
            response_j1  = json.loads(cleaned)

       
        logger.debug(f" Json loaded Type { type(response_j1)} ")

        response_json  = response_j1
        print(f" Formatted JSON : {response_json}")   
        response_json = json.dumps(response_json,indent=4)    
        
    return response_json

def add_to_list(json_text:json,category:str):

    print(f" add to list : {json_text}")

    prohibitions = ["sanction","boycott"]
    json_t = json.dumps(json_text,indent=4)
    response_j = json.loads(json_t)
    print(f" response_j {response_j}")
    list_ptext = []
    dict_p_text = {}
    if category in prohibitions:
        response_json = [record for record in response_j if record["category"].lower() == category ] 
        for entry in response_json:
            print(f"entry :  {entry}")
            list_ptext.append(entry["prohibition_text"])
        dict_p_text["category"]  = category
        dict_p_text["prohibition_text"] = list_ptext



    print(f"Returning {dict_p_text}")

    return dict_p_text


def filter_response(raw_response_json, startch, endch):
    raw_response_json = raw_response_json
    try:
        start_ind = raw_response_json.index(startch)
        end_ind = raw_response_json.find(endch,start_ind+1)
        return raw_response_json[start_ind:end_ind + 1]
    except ValueError:
        return "{}"


if __name__ == "__main__":
    sample_swift_input = ""
    sample_lc_file = os.path.join("resources", "sample_lc.json")
    p_text = "Question: What are the prohibitions related to international trade finance that are mentioned in provided text?  . \n List all the prohibitions one by one without repeating and caegorize the same as 'Boycott', 'Sanction' or 'Others'. \n Return  response as a valid structured JSON Only with 'category' and 'prohibition_text' (WITHOUT ANY CHANGES TO ORIGINAL TEXT OR ANY SPELLING CORRECTIONS) for each prohibition. DO NOT ADD ANY OTHER DETAILS OF YOUR OWN. In case of no prohibitions are found return blank response.\n"

    response = """{
    content='```json\n[\n {\n "category": "Sanction",\n "prohibition_text": "DUBAI BANK FOR INVESTMENT AND FOREIGN TRADE (AGENCY) MIGHT BE SUBJECT TO AND AFFECTED BY, SANCTIONS, WITH WHICH IT WILL COMPLY."\n },\n {\n "category": "Sanction",\n "prohibition_text": "AGENCY IS NOT REQUIRED TO PERFORM ANY OBLIGATION UNDER THIS CREDIT WHICH IT DETERMINES IN ITS ABSOLUTE DISCRETION WILL OR WOULD BE LIKELY TO, CONTRAVENE OR BREACH OF ANY SANCTION."\n },\n {\n "category": "Others",\n "prohibition_text": "THIRD PARTY DOCUMENTS ARE NOT ALLOWED"\n }\n]\n```' additional_kwargs={} response_metadata={'model': 'phi4:14b', 'created_at': '2025-07-28T17:49:22.036606909Z', 'done': True, 'done_reason': 'stop', 'total_duration': 41311717004, 'load_duration': 27656701, 'prompt_eval_count': 724, 'prompt_eval_duration': 24795241052, 'eval_count': 159, 'eval_duration': 16488078589, 'model_name': 'phi4:14b'}"""

    json_obj = json.dumps(response,indent=4)
    print(filter_response(json_obj,"[","]"))
    response_json = filter_response(json_obj,"[","]")
    cleaned = response_json.encode('utf-8').decode('unicode_escape')  # unescape the \n and \" etc.
    parsed = json.loads(cleaned)
    print(parsed)
    #response_json = json.loads(response_json)

    for record in parsed:
        print(record) 
    dict_ptext = add_to_list(parsed,"sanction")
    #response_j1 = dict_ptext

    print(dict_ptext)

    try:
        with open(sample_lc_file, "r") as f:
            sample_swift_input = f.read()
        call_baoe_service(sample_lc_file,"sanction")
    except FileNotFoundError:
         print(f"Error: The file '{sample_lc_file}' was not found.")
         #exit()
    # print(tag_prohibitions(p_context=sample_swift_input,category="boycott"))

