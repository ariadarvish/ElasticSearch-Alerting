#!/usr/bin/python3

import redis 
from enum import Enum
import json
import socket
import requests


r = redis.Redis()

slack_webhook = "<slack_webhook_url>"

try:
    r.ping()
    print("Connection to Redis : Successful")
except:
    print("Connection to Redis : Failed")
    

class Result(Enum):
    Error = 1
    Ok = 2
    Empty = 3

def get_errors():
    try:
        error_json = r.get("elastic_errors")
        decoded_error_json = error_json.decode('ascii')
        error_list = json.loads(decoded_error_json)
        #print(error_list)
        return error_list
    except:
        print("error")


def error_key_existance():
    key_exists = r.exists("elastic_errors")

    if key_exists:
       return Result.Ok
    else:
        return Result.Empty

def send_message(datetime,server_info,error_text):
  
    # Define the message payload
    payload = {
         'text': f'*{datetime}* \n>*Server:* {server_info} \n>*Description:* {error_text}'
    }

    # Send the message to Slack
    response = requests.post(
        slack_webhook,
        data=json.dumps(payload),
        headers={'Content-Type': 'application/json'}
    )

    # Check if the message was sent successfully
    if response.status_code == 200:
        print("Message sent successfully")
       
        
    else:
        print("Failed to send message:", response.text)
        # Update the value of the gauge metric
       
def get_server_info():
    hostname = socket.gethostname()
    # Get the IP address corresponding to the hostname
    ip_address = socket.gethostbyname(hostname)
    server_info = f"{hostname} {ip_address}"

    return server_info

key_existance = error_key_existance()
if(key_existance  == Result.Ok):
    server_info = get_server_info()

    response = get_errors()

    error_datetime = response[0]

    for i in range(1,len(response)):
        send_message(error_datetime,server_info,response[i])
        #print(response[i])

    r.delete("elastic_errors")
