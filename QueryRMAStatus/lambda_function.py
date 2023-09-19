import boto3
import json
from boto3.dynamodb.conditions import Key
from datetime import datetime

FUNCTION_NAME = 'team16_hackathon_QueryRMAHistory'
PRODUCT_TABLE = 'team16_hackthon_product_info'

lambda_client = boto3.client('lambda')
dynamo = boto3.resource('dynamodb')

def lambda_handler(event, context):
    intent_request = event
    
    session_attributes = intent_request['sessionState']['sessionAttributes']
    session_attributes['sessionId'] = intent_request['sessionId']
    
    slots = intent_request['sessionState']['intent']['slots']
    
    phoneNumber = slots['PhoneNumber'] if 'PhoneNumber' in slots else None
    notContinue = slots['RMAIndex_or_Not']['subSlots']['Continue'] if 'Continue' in slots['RMAIndex_or_Not']['subSlots'] else None
    RMAIndex = slots['RMAIndex_or_Not']['subSlots']['Index'] if 'Index' in slots['RMAIndex_or_Not']['subSlots'] else None  
    
    if notContinue == None and RMAIndex == None:        
        payload = json.dumps({'PhoneNumber': phoneNumber['value']['originalValue']}) 
        response = lambda_client.invoke(FunctionName=FUNCTION_NAME, Payload=payload)
        RMA_list = json.loads(response['Payload'].read().decode('utf-8'))
        
        session_attributes['RMA_list'] = json.dumps(RMA_list)
        
        message = 'Below is your RMA List. Please select one to continue.'
        RMA_message_list = []
        for index, item in enumerate(RMA_list):
            temp_message = f'{index+1}.\n'
            temp_message += f'Product Name: {item["ProductName"]}\n'
            temp_message += f'Serial Number: {item["SerialNumber"]}\n'
            temp_message += f'RMA Status: {item["RepairStatus"]}'
            RMA_message_list.append(temp_message)
        
        result = {
            'sessionState': {
                'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'ElicitSlot',
                    'slotToElicit': 'RMAIndex_or_Not'
                },
                'intent': intent_request['sessionState']['intent']
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': message
                }
            ]
        }
        for item in RMA_message_list:
            result['messages'].append({
                'contentType': 'PlainText',
                'content': item
            })
        
        return result
    elif notContinue != None and RMAIndex == None:
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'Close'
                },
                'intent': intent_request['sessionState']['intent']
            },
            'messages': [{
                'contentType': 'PlainText',
                'content': 'Got it!\nThank you for using our service. Have a nice day!'
            }]
        }
    elif notContinue == None and RMAIndex != None:
        target_RMA = json.loads(session_attributes['RMA_list'])[int(RMAIndex['value']['interpretedValue'])-1]
        type = dynamo.Table(PRODUCT_TABLE).query(
            KeyConditionExpression=Key('SerialNumber').eq(target_RMA['SerialNumber'])
        )['Items'][0]['Type']
        
        message = "Here is your detailed information on this RMA recorded"
        
        RMA_info = f'Product Name: {target_RMA["ProductName"]}\n'
        RMA_info += f'Type: {type}\n'
        RMA_info += f'Serial Number: {target_RMA["SerialNumber"]}\n'
        RMA_info += f'Reason: {target_RMA["RepairReason"]}\n'
        RMA_info += f'RMA Status: {target_RMA["RepairStatus"]}\n'
        RMA_info += f'Service Center: {target_RMA["RepairPlace"]}\n'
        RMA_info += f'RMA Published Date: {target_RMA["RepairStartDate"]}'
        if "RepairEndDate" in target_RMA:
            RMA_info += '\n'
            RMA_info += f'RMA Completed Date: {target_RMA["RepairEndDate"]}'
        
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'Close'
                },
                'intent': intent_request['sessionState']['intent']
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': message
                },
                {
                    'contentType': 'PlainText',
                    'content': RMA_info
                }
            ]
        }