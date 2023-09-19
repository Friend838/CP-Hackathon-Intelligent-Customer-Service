import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from ResponseFormatter import *
from FunUtili import *
import random

PRODUCT_TABLE = 'team16_hackthon_product_info'
REGISTRATION_TABLE = 'team16_hackthon_product_registration'

dynamodb_resource = boto3.resource('dynamodb')

def lambda_handler(event, context):
    intent_request = event
    
    session_attributes = intent_request['sessionState']['sessionAttributes']
    session_attributes['sessionId'] = intent_request['sessionId']
    
    slots = intent_request['sessionState']['intent']['slots']
    phoneNumber = slots['PhoneNumber'] if 'PhoneNumber' in slots else None
    serialNumber = slots['SerialNumber'] if 'SerialNumber' in slots else None
    purchasedDate = slots['PurchasedDate'] if 'PurchasedDate' in slots else None
    
    if intent_request['sessionState']['intent']['confirmationState'] == 'Confirmed':
        message1 = [
            'Your confirmation is greatly appreciated. We will take care of your request promptly.',
            'Thank you for confirming your details. We will proceed with your request and provide you with the best possible service.',
            'Thank you for verifying your information. We will continue with your request and provide you with the necessary assistance.'
        ]
        
        message2 = "And the most important, we are grateful that you choose our product. We're excited to have you as a customer and look forward to serving you."
        

        dynamodb_resource.Table(REGISTRATION_TABLE).put_item(
            Item=json.loads(session_attributes['new_item'])
        )
        
        session_attributes = {
            'sessionId': intent_request['sessionId']
        }

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
                    'content': random.choice(message1)
                },
                {
                    'contentType': 'PlainText',
                    'content': message2
                }
            ]
        }
    elif intent_request['sessionState']['intent']['confirmationState'] == 'Denied':
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
                    'content': "It's fine. We can repeat again."
                }
            ]
        }
    
    if phoneNumber != None and serialNumber != None and purchasedDate != None:
        productInfo = dynamodb_resource.Table(PRODUCT_TABLE).query(
            KeyConditionExpression=Key('SerialNumber').eq(serialNumber['value']['originalValue'])
        )['Items'][0]
        
        productName = productInfo['ProductName']
        warrantyPeriod = int(productInfo['WarrantyPeriod'])
        type = productInfo['Type']
        year, month, day = purchasedDate['value']['interpretedValue'].split('-')
        
        new_item = {
            'PhoneNumber': phoneNumber['value']['originalValue'],
            'SerialNumber': serialNumber['value']['originalValue'],
            'ProductName': productName,
            'Type': type,
            'PurchasedDate': purchasedDate['value']['interpretedValue'],
            'WarrantyEndDate': datetime(int(year)+warrantyPeriod, int(month), int(day)).strftime('%Y-%m-%d')
        }
        
        session_attributes['new_item'] = json.dumps(new_item)
        
        message = 'Below is your product registration information. Please check'
        information = f'Phone Number: {new_item["PhoneNumber"]}\n'
        information += f'Product Name: {new_item["ProductName"]}\n'
        information += f'Type: {new_item["Type"]}\n'
        information += f'Serial Number: {new_item["SerialNumber"]}\n'
        information += f'Purchased Date: {new_item["PurchasedDate"]}\n'
        information += f'Warranty End Date: {new_item["WarrantyEndDate"]}\n'
        return {
            "sessionState": {
                "sessionAttributes": session_attributes,
                "dialogAction": {
                    "type": "ConfirmIntent"
                },
                "intent": intent_request['sessionState']['intent']
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": message
                },
                {
                    "contentType": "PlainText",
                    "content": information
                }
            ]
        }