import boto3
import json
from datetime import datetime

LAMBDA_NAME = 'team16_hackthon_QueryUserProduct'
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    intent_request = event
    
    session_attributes = intent_request['sessionState']['sessionAttributes']
    session_attributes['sessionId'] = intent_request['sessionId']
    
    slots = intent_request['sessionState']['intent']['slots']
    
    phoneNumber = slots['PhoneNumber'] if 'PhoneNumber' in slots else None
    serialNumber = slots['SerialNumber'] if 'SerialNumber' in slots else None
    
    if phoneNumber != None and serialNumber != None:
        payload = json.dumps({
            'PhoneNumber': phoneNumber['value']['originalValue'],
            'SerialNumber': serialNumber['value']['originalValue']
        })
        response = lambda_client.invoke(FunctionName=LAMBDA_NAME, Payload=payload)
        print(response)
        target_product = json.loads(response['Payload'].read().decode('utf-8'))[0]
        print(target_product)
        
        purchaseDate = datetime.strptime(target_product['PurchasedDate'], '%Y-%m-%d').strftime('%Y-%m-%d')
        
        message1 = "Here is your product warranty information."
        productInfo = f"Product Name: {target_product['ProductName']}\n"
        productInfo += f"Product Type: {target_product['Type']}\n"
        productInfo += f"Serial Number: {target_product['SerialNumber']}\n"
        productInfo += f"Purchased Date: {purchaseDate}\n"
        productInfo += f"Warranty Expiration Date: {target_product['WarrantyEndDate']}"
        message2 = "Thank you for using our service!"
        
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'Close'
                },
                'intent': intent_request['sessionState']['intent'],
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': message1
                },
                {
                    'contentType': 'PlainText',
                    'content': productInfo
                },
                {
                    'contentType': 'PlainText',
                    'content': message2   
                }
            ]
        }