import json
import os
from logger_config import logger


def keyMapping(aKey):
    doc2json = {'SWIFT OUTPUT': "SwiftOut", 'SENDER': "LCSender", 'RECEIVER': "LCReceiver", 
        '20': "LCRefNo", 
        '21': "LCTransRefNo", 
        '27': "LCSequenceOfTotal",         
        '31C': "LCDateOfIsuue", 
        '31D': "LCDatePlaceExpiry", 
        '32B': "LCCurrencyCodeAmount", 
        '39A': "LCCreditAmtTolerance1", 
        '39B': "", 
        '39C': "", 
        '40A': "LCFormOfDocumentaryCredit",
        '40B': "LCFormOfDocumentaryCredit",
        '40E': "LCApplicableRules", 
        '41A': "", 
        '41D': "LCAvailableWithBy", 
        '42A': "LCDrawee", 
        '42C': "LCDraftAt", 
        '43P': "LCPartialsShipment", 
        '43T': "LCTranshipmentCode", 
        '44A': "LCPlaceOfDispatch",
        '44B': "LCPlaceOfDelivery", 
        #'44A': "LCPlaceOfReceipt",
        #'44B': "LCPlaceOfDelivery",
        '44C': "LCLatestDateOfShipment", 
        '44E': "LCPortOfLoading",
        '44F': "LCPortOfDischage", 
        '45A': "LCDescriptionOfGoods", 
        '46A': "LCDocumentRequired", 
        '46B': "LCDocumentRequired", 
        '47A': "LCAdditionalCondition", 
        '48': "LCPeriodForPresentationDays", 
        '49': "LCConfirmationInstruction",
        '50': "LCApplicantNameAndAddress", 
        '52A': "LCIssuingBank", 
        '53A': "LCReimbursingBank", 
        '57A': "LCAdviseThroughBank",
        '59': "LCBeneNameAndAddress", 
        '71D': "LCCharges", 
        '72Z': "LCSenderToReceiverInfo", 
        '78': "LCInstructionToThePaying"}
    
    if ((aKey not in doc2json) or (doc2json.get(aKey)== "")):
        logger.debug("Key not found for ", aKey)
        return ""
    return doc2json.get(aKey)

# check with Vikram 53A

def parse_input_with_header_and_body(input_data):
    logger.info("parse_input_with_header_and_body : START 1")
    lc_data_key_arr = []
    lc_data_val_arr = []

    #decode input data
    input_data_enc = input_data#decode('utf-8')

    #print(f"input_data_enc : {input_data_enc}")

    current_key = None
    current_value = []
    in_body = False

    input_lines = input_data_enc.split("\n")
    print(f"INPUT LINES : {input_lines}")

    for line in input_lines:
        print(f" LINE  =        : {line}")
        if not(isinstance(line,int)) :
        #line = " ".join(line.split())
            line = line.replace("\u2013", "-")
            line = line.replace("\u2018", "\'")
            line = line.replace("\u2019", "\'")
            line = line.replace("\u2026", ".")
            #line = " ".join(line)
       

            # Check for the separator between two messages
            if line.find("$$Next Message$$") >= 0:
                in_body = False
                if current_key:
                    lc_data_key_arr.append(current_key)
                    lc_data_val_arr.append("".join(current_value).strip())
                    
                current_key = None
                current_value = []
                continue
            # Check for the separator between header and body
            if line.find("Message Text") >= 0:
                in_body = True
                # Save the last header key-value pair
                if current_key:
                    lc_data_key_arr.append(current_key)
                    lc_data_val_arr.append(" ".join(current_value).strip())
                    
                current_key = None
                current_value = []
                continue

            if in_body:
                # Parse body section where keys start and end with ":"
                if line.startswith(":") and ":" in line[1:]:
                    if current_key:
                        # Save the previous key-value pair
                        lc_data_key_arr.append(current_key)
                        lc_data_val_arr.append(" ".join(current_value).strip())
                        
                    current_key = line.strip(":")
                    current_value = []  # Reset for the new key
                elif current_key:  # Add to the current value
                    current_value.append(line)
            else:
                # Parse header section where key and value are separated by ":"
                if ":" in line:
                    if current_key:
                            # Save the previous key-value pair
                        lc_data_key_arr.append(current_key)
                        lc_data_val_arr.append(" ".join(current_value).strip())
                        
                        
                    key, value = map(str.strip, line.split(":", 1))
                    current_key = key
                    current_value = [value]  # Start the value
                elif current_key:  # Add to the current value
                    current_value.append(line)

    # Save the last key-value pair
    if current_key:
        lc_data_key_arr.append(current_key)
        lc_data_val_arr.append(" ".join(current_value).strip())
    
    logger.info("parse_input_with_header_and_body : END ")
    return {'keys':lc_data_key_arr, 'vals':lc_data_val_arr}
        

def process_input(input_data):
    logger.info("process_input() : START ")
    logger.info(f" input data : {input_data}")
    parsed_data_dict = parse_input_with_header_and_body(input_data)

    print(f"Parsed {parsed_data_dict}")
        
    parsed_data_keys = parsed_data_dict.get('keys')
    parsed_data_vals = parsed_data_dict.get('vals')
        
        
    count = 0
    keyList = []
    final_out = {}
    while (count < len(parsed_data_keys)):
        aKey = parsed_data_keys[count]
        aVal = parsed_data_vals[count]
        key_1 = None
        key_2 = None
            
        storedList = []
            
        key_in_2_parts = aKey.split(":", 1)
        key_1 = key_in_2_parts[0].upper()
            
        if len(key_in_2_parts) > 1 :
            key_2 = key_in_2_parts[1]
        key_1_final = keyMapping(key_1)
        if key_1_final != "" :
            if(key_1_final not in final_out):
                keyList.append(key_1_final)
                final_out[key_1_final] = aVal
            else :
                storedVal = final_out.get(key_1_final)
                if not isinstance(storedVal, list):
                    storedList.append(storedVal)
                else: 
                    storedList = storedVal
                storedList.append(aVal)
                final_out[key_1_final] = storedList
            
        count = count + 1

    #special treatment for 20
    #Make it ',' separated string.
    if ("LCRefNo" in final_out and isinstance(final_out.get("LCRefNo"), list)):
        vLCRefs = ", ".join(final_out.get("LCRefNo")).strip()
        final_out["LCRefNo"] = vLCRefs
            
    #special treatment for 27
    #Make it an array, even if single value is present.
    if ("LCSequenceOfTotal" in final_out and not isinstance(final_out.get("LCSequenceOfTotal"), list)):
        final_out["LCSequenceOfTotal"] = [final_out.get("LCSequenceOfTotal")]
            
    #special treatment for 31D
    if ("LCDatePlaceExpiry" in final_out):            
        if isinstance(final_out.get("LCDatePlaceExpiry"), list):
            vLCDatePlaceExpiry = final_out.get("LCDatePlaceExpiry")[0]
        else:
            vLCDatePlaceExpiry = final_out.get("LCDatePlaceExpiry")
                
        vLCDatePlaceExpirySplit = vLCDatePlaceExpiry.split(" ",1)
            
        pos = list(final_out.keys()).index('LCDatePlaceExpiry')
        items = list(final_out.items())
        items.insert(pos, ('LCDateExpiry', vLCDatePlaceExpirySplit[0]))
        items.insert(pos + 1, ('LCPlaceExpiry', vLCDatePlaceExpirySplit[1]))
        final_out = dict(items)
            
        final_out.pop("LCDatePlaceExpiry")
            
    #special treatment for 32B
    if ("LCCurrencyCodeAmount" in final_out):
        if isinstance(final_out.get("LCCurrencyCodeAmount"), list):
            vLCCurrencyCodeAmount = final_out.get("LCCurrencyCodeAmount")[0]
        else:
            vLCCurrencyCodeAmount = final_out.get("LCCurrencyCodeAmount")
        vLCCurrencyCodeAmountSplit = vLCCurrencyCodeAmount.split(" ",1)
            
        pos = list(final_out.keys()).index('LCCurrencyCodeAmount')
        items = list(final_out.items())
        items.insert(pos, ('LCCurrencyCode', vLCCurrencyCodeAmountSplit[0]))
        items.insert(pos + 1, ('LCAmount', vLCCurrencyCodeAmountSplit[1]))
        final_out = dict(items)
        
        final_out.pop("LCCurrencyCodeAmount")
        
    #special treatment for field SwiftOutput
    #Two mandatory fields LCMsgType and LCMsgAdvice. If no value, send ""
    if ("SwiftOut" in final_out):
        if isinstance(final_out.get("SwiftOut"), list):
            vLCSwiftOut = final_out.get("SwiftOut")[0]
        else:
            vLCSwiftOut = final_out.get("SwiftOut")
        vLCSwiftOutSplit = vLCSwiftOut.split(" ",1)
            
        #final_out["LCMsgType"] = vLCSwiftOutSplit[0]
        #final_out["LCMsgAdvice"] = vLCSwiftOutSplit[1]
            
        pos = list(final_out.keys()).index('SwiftOut')
        items = list(final_out.items())
        items.insert(pos, ('LCMsgType', vLCSwiftOutSplit[0]))
        items.insert(pos + 1, ('LCMsgAdvice', vLCSwiftOutSplit[1]))
        final_out = dict(items)
            
        final_out.pop("SwiftOut")
    else:
        pos = 0
        items = list(final_out.items())
        items.insert(pos, ('LCMsgType', ""))
        items.insert(pos + 1, ('LCMsgAdvice', ""))
        final_out = dict(items)
        
    #special treatment for field Sender & Receiver
    #There should be one sender and one receiver
    if ("LCSender" in final_out and isinstance(final_out.get("LCSender"), list)):
        vLCSender = final_out.get("LCSender")[0]
        final_out["LCSender"] = vLCSender
    if ("LCReceiver" in final_out and isinstance(final_out.get("LCReceiver"), list)):
        LCReceiver = final_out.get("LCReceiver")[0]
        final_out["LCReceiver"] = LCReceiver
        
    #special treatment for field 45A
    #Concatenate if there are more than one message
    if ("LCDescriptionOfGoods" in final_out and isinstance(final_out.get("LCDescriptionOfGoods"), list)):
        vLCGoods = " ".join(final_out.get("LCDescriptionOfGoods")).strip()
        final_out["LCDescriptionOfGoods"] = vLCGoods
        
    #special treatment for field 46A
    #Concatenate if there are more than one message
    if ("LCDocumentRequired" in final_out and isinstance(final_out.get("LCDocumentRequired"), list)):
        vLCDocsReqd = " ".join(final_out.get("LCDocumentRequired")).strip()
        final_out["LCDocumentRequired"] = vLCDocsReqd
        
    #special treatment for field 47A
    #Concatenate if there are more than one message
    if ("LCAdditionalCondition" in final_out and isinstance(final_out.get("LCAdditionalCondition"), list)):
        vLCAddlCond = " ".join(final_out.get("LCAdditionalCondition")).strip()
        final_out["LCAdditionalCondition"] = vLCAddlCond
        
    logger.info("process_input() : END ")
    print(f"Converted to JSON : {final_out}")

    return final_out

if __name__ == "__main__":
    sample_lc_file = "resources" + os.sep + "sample_lc.txt"

    try:
        sample_swift_input =""
        with open(sample_lc_file, "r",encoding="UTF-8") as sampl_lc:
            sample_swift_input = sampl_lc.read()

        print (f" Read File : {sample_swift_input}")

        processed = process_input(sample_swift_input)
        print(processed)
    except FileNotFoundError:
        print(f"Error: The file '{sample_lc_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_json():

    str_input = ""
    with open ("resources/sample_lc.json") as lc_j:
        str_input = lc_j.read()
    
    json_lc = ""
    if lc_j:
        json_lc = json.loads(str_input)
    return json_lc

