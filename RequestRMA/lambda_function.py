import boto3
import json
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta
from ResponseFormatter import *

REGISTRATION_TABLE = 'team16_hackthon_product_registration'
CENTER_TABLE = 'team16_hackthon_center_location'
RMA_TABLE = 'team16_hackthon_RMA'

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    intent_request = event
    
    session_attributes = intent_request['sessionState']['sessionAttributes']
    session_attributes['sessionId'] = intent_request['sessionId']
    
    slots = intent_request['sessionState']['intent']['slots']
    
    phoneNumber = slots['PhoneNumber'] if 'PhoneNumber' in slots else None
    targetIndex = slots['TargetIndex'] if 'TargetIndex' in slots else None
    reason = slots['Reason'] if 'Reason' in slots else None
    neededRMA = slots['NeededRMA'] if 'NeededRMA' in slots else None
    location = slots['Location'] if 'Location' in slots else None
    shippingMethod = slots['ShippingMethod'] if 'ShippingMethod' in slots else None
    serviceCenterIndex = slots['ServiceCenterIndex'] if 'ServiceCenterIndex' in slots else None

    
    if targetIndex == None:
        registered_product = dynamodb.Table(REGISTRATION_TABLE).scan(
            FilterExpression=Key('PhoneNumber').eq(phoneNumber['value']['originalValue'])
        )['Items']
        
        session_attributes['all_products'] = json.dumps(registered_product)
        
        message = 'Please choose one of the following registered products:\n'
        product_list = []
        for index, item in enumerate(registered_product):
            temp_message = f'{index+1}.\n'
            temp_message += f'Product Name: {item["ProductName"]}\n'
            temp_message += f'Serial Number: {item["SerialNumber"]}\n'
            temp_message += f'Purchased Date: {item["PurchasedDate"]}\n\n'
            product_list.append(temp_message)
        
        result = {
            'sessionState': {
                'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'ElicitSlot',
                    'slotToElicit': 'TargetIndex'
                },
                'intent': intent_request['sessionState']['intent'],
            },
            'messages': [{
                    'contentType': 'PlainText',
                    'content': message
            }]
        }
        
        for item in product_list:
            result['messages'].append({
                'contentType': 'PlainText',
                'content': item
            })
        
        return result
    
    elif neededRMA == None:
        if reason['value']['interpretedValue'] == 'by person':
            intent_request['sessionState']['intent']['state'] = 'Fulfilled'
            
            return {
                'sessionState': {
                    'sessionAttributes': session_attributes,
                    'dialogAction': {
                        'type': 'Close'
                    },
                    'intent': intent_request['sessionState']['intent']
                },
                'messages': [{
                    'contentType': 'PlainText',
                    'content': 'We are unable to provide an RMA to you as this is caused by human error.'
                }]
            }
        else:
            all_products = json.loads(session_attributes['all_products'])
            target_product = all_products[int(targetIndex['value']['interpretedValue'])-1]
            
            session_attributes = {
                'sessionId': intent_request['sessionId'],
                'target_product': json.dumps(target_product)
            }

            message = 'Based on your product type, here are some simple solutions for your reference.\n'
            if target_product['Type'] == 'GPU':
                message += '1. Is your power cable correctly connected to your graphics card?\n'
                message += '2. Is your graphics card fully inserted into the PCIE slot?\n'
                message += '3. Is your monitor output cable plugged into the integrated graphics?\n\n'
            elif target_product['Type'] == 'PowerSupply':
                message += '1. Is your power cable correctly connected to your power supply?\n'
                message += '2. Is your power supply wattage suitable for your computer spec?\n'
                message += '3. If possible, transfer to another computer to test it works or not\n'
                
            confirmation = 'Do you still need RMA? Please reply with Yes or No.'
            
            return {
                'sessionState': {
                    'sessionAttributes': session_attributes,
                    'dialogAction': {
                        'type': 'ElicitSlot',
                        'slotToElicit': 'NeededRMA'
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
                        'content': confirmation
                    }
                ]
            }
    elif shippingMethod == None:
        centers = dynamodb.Table(CENTER_TABLE).query(
            KeyConditionExpression=Key('location').eq(location['value']['originalValue'])
        )['Items'][0]
        
        session_attributes['available_centers'] = json.dumps(centers['ServiceCenters'])
        
        return {
            'sessionState': {
                'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'ElicitSlot',
                    'slotToElicit': 'ShippingMethod'
                },
                'intent': intent_request['sessionState']['intent']
            }
        }
    elif serviceCenterIndex == None:
        message = 'Got it. According to your location, below are our service centers near you.\n'
        
        print(session_attributes['available_centers'])
        for index, center in enumerate(json.loads(session_attributes['available_centers'])):
            message += f'{index+1}. {center}\n'
            
        confirmation = 'Which one do you prefer?\n'
        
        return {
            'sessionState': {
                'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'ElicitSlot',
                    'slotToElicit': 'ServiceCenterIndex'
                },
                'intent': intent_request['sessionState']['intent']
            },
            'messages':[
                {
                    'contentType': 'PlainText',
                    'content': message
                },
                {
                    'contentType': 'PlainText',
                    'content': confirmation
                }
            ]
        }
    elif intent_request['sessionState']['intent']['confirmationState'] == 'None':
        item = {}
        item['PhoneNumber'] = phoneNumber['value']['originalValue']
        item['SerialNumber'] = json.loads(session_attributes['target_product'])['SerialNumber']
        item['ProductName'] = json.loads(session_attributes['target_product'])['ProductName']
        item['RepairReason'] = reason['value']['originalValue']
        item['RepairPlace'] = json.loads(session_attributes['available_centers'])[int(serviceCenterIndex['value']['interpretedValue'])-1]
        item['RepairStartDate'] = (datetime.now()+timedelta(hours=8)).strftime("%Y-%m-%d")
        item['RepairStatus'] = 'Not Received'
        
        session_attributes['rma_info'] = json.dumps(item)
        
        message = 'Below is your RMA information, please check it is correct\n'
        message += f'Phone Number: {item["PhoneNumber"]}\n'
        message += f'Product Name: {item["ProductName"]}\n'
        message += f'Serial Number: {item["SerialNumber"]}\n'
        message += f'RMA Reason: {item["RepairReason"]}\n'
        message += f'Service Center: {item["RepairPlace"]}\n'
        message += f'RMA Start Date: {item["RepairStartDate"]}\n'
        
        return {
            'sessionState': {
                'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'ConfirmIntent'
                },
                'intent': intent_request['sessionState']['intent']
            },
            'messages': [{
                'contentType': 'PlainText',
                'content': message
            }]
        }
    else:
        item = json.loads(session_attributes['rma_info'])
        dynamodb.Table(RMA_TABLE).put_item(Item=item)
        
        message1 = 'Your RMA has been recorded.'
        if shippingMethod['value']['interpretedValue'] == 'Self-delivery':
            message2 = 'Since you have chosen to self-deliver, please deliver to our service center within one week.'
        else:
            message2 = 'Due to your choice of shipping via freight company, please be prepared for their arrival within three days.'
        message3 = 'What really matters is that we are sorry that our product has caused you such an issue.\n'
        message3 += 'We hope our follow-up service can earn your continued support.'
                
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
                    'content': message1
                },
                {
                    'contentType': 'PlainText',
                    'content': message2
                },
                {
                    'contentType': 'PlainText',
                    'content': message3
                }
            ]
        }
        
        