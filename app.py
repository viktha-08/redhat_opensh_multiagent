from dotenv import load_dotenv
from flask import Flask, flash, request, jsonify, render_template, send_from_directory
from flask_basicauth import BasicAuth
import json
from logger_config import logger
from multi_agent_ollama_router import get_workflow
import prohibitions_handler as ask_w
import asyncio

app = Flask(__name__)

app.config['BASIC_AUTH_USERNAME'] = "testuser1"
app.config['BASIC_AUTH_PASSWORD'] = "45$124K#aH"

basic_auth = BasicAuth(app)

# Import the workflow factory function from our other file

# This is efficient as it avoids recompiling on every request.
langgraph_app = get_workflow()
# --- 1. Application Setup ---

# Load environment variables from .env file (for the OPENAI_API_KEY)
load_dotenv()

def load_config():
    
  load_dotenv(override=True)
  
# Setup Flask App
def setup_flask():
    logger.info("Setting up flask")


@app.route("/",methods=["GET","POST"])
def hello_world():
    result = {"success": "Welcome to GenAI app." }
    response = app.response_class(json.dumps(result,indent=6), status=200, mimetype='application/json')
    return response


@app.route("/call_agent", methods=["POST"])
@basic_auth.required
def invoke_agentic_workflow():

    print(" INVOKE AHENT ")
    cleaned = request.get_data()
    #cleaned = payload_.encode('utf-8').decode('unicode_escape')
    print(f" PAYLOAD : {cleaned}")

    initial_state = {
        "input_swift_text": cleaned,
        "lc_json_data": None,
        "prohibition_results": None,
        "goods_details": None,
        "dns_result": None,
    }

    try:
        print("--- API: STARTING WORKFLOW INVOCATION ---")
        # Use the compiled app to run the workflow asynchronously
        final_state = asyncio.run(langgraph_app.ainvoke(initial_state))
        
        print(f"\n--- API: FINAL STATE --- {final_state}")

        agent_response = {}

        agent_response ["prohibition_results"] = final_state["prohibition_results"]
        agent_response ["goods_details"] = final_state["goods_details"]
        agent_response ["dns_result"] = final_state["dns_result"]

        response_json = {}
        response_json["request"] = final_state["lc_json_data"]
        response_json["agent_response"] = agent_response
        print(json.dumps(response_json, indent=2))
        response_data = json.dumps(response_json, indent=2)
        response = app.response_class( response_data, status=200, mimetype='application/json')
        return response

       
    except ValueError as e:
        # Specifically catch the missing API key error from the workflow
        print(f"ValueError during workflow: {e}")
        raise Exception(status_code=500, detail=str(e))
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred during workflow: {e}")
        raise Exception(status_code=500, detail="An internal error occurred.")




@app.route("/call_llm", methods=["POST"])
@basic_auth.required
def call_llm():
    logger.info(" call_llm() --- START")

    prompt_desc = ""
    prompt_context = ""
    prompt_category = ""

    try:
        payload_ = request.get_data()
        json_payload:json = json.loads(payload_.strip())
        
        if json_payload["p_text"]:
            prompt_desc = json_payload["p_text"].strip()

        if json_payload["p_context"]:
            prompt_context = json_payload["p_context"].strip()
        
        if json_payload["p_category"]:
            prompt_category = json_payload["p_category"].strip()

    except Exception as ex:
        logger.error(f"Generic error {ex}")
    
    error_occured = False
    try:
        response = ""
        if prompt_desc and prompt_context:
 
            response_data = ask_w.run_prompt( prompt_desc, prompt_context ,prompt_category)
            logger.info("LLM response received ")
            if response_data:
                logger.debug("====== creating response")
                
                response = app.response_class( response_data, status=200, mimetype='application/json')
            else:
                result = {"error": "Error  occured while processing request, response not generated" }
                response = app.response_class(json.dumps(result,indent=4), status=500, mimetype='application/json')

    except Exception as ex:
        print(f"Exception is {ex}")

    return response



if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0", port=8080)


""" def main():
    process_order()

if __name__ == "__main__":
    main() """
