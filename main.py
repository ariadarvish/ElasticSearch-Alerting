#!/usr/bin/python3

import requests
import json
from enum import Enum
import redis
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway


#prometheus - push gateway 
# Create a registry to hold metrics
registry = CollectorRegistry()
# Define a gauge metric
label_names = ['label1', 'label2']
gauge_metric = Gauge('healthcheck_metric', 'general application healthcheck',labelnames=label_names, registry=registry)
#gauge_metric.set_to_current_time()


r = redis.Redis()
try:
    r.ping()
    print("Connection to Redis : ", r.ping())
except:
    gauge_metric.set(0)
    print("Connection to Redis : Failed")

headers = {
    'Content-Type': 'application/json',
}

json_data = {
    'size': 0,
    'query': {
        'bool': {
            'must': [
                {
                    'match': {
                        'status.keyword': '200',
                    },
                },
                {
                    'range': {
                        '@timestamp': {
                            'gte': 'now-5m',
                            'lte': 'now',
                        },
                    },
                },
            ],
        },
    },
    'aggs': {
        'top_organizations': {
            'terms': {
                'field': 'organization.keyword',
                'size': 5,
            },
        },
    },
}

bytes_data = requests.get('http://<your_server_ip:port>/cdn-accesslog-new*/_search', headers=headers, json=json_data)


# function - send message to slack function 
def send_message(key,percent):
    # Define the webhook URL
    webhook_url = 'slack_webhook_url'

    #get requests count
    requests_count = get_value_from_redis(key)
    string_requests_count = requests_count.decode('ascii')

    # Define the message payload
    payload = {
         'text': f'*Drop over RPS* :alert: \n>*Provider:* {key} \n>*Drop Rate:* {int(percent)}% \n>*Requests: {int(string_requests_count)}*'
    }

    # Send the message to Slack
    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={'Content-Type': 'application/json'}
    )

    # Check if the message was sent successfully
    if response.status_code == 200:
        print("Message sent successfully")
       
        
    else:
        print("Failed to send message:", response.text)
        # Update the value of the gauge metric
        gauge_metric.set(0)



#declare enum for returning the result of checking log file
class Result(Enum):
    Error = 1
    Ok = 2
    Empty = 3


#function - check redis 
def check_previous_data_existance():
   
      cursor, keys = r.scan()
      if not keys:
          return Result.Empty
        
      else:
          return Result.Ok

#get value from redis
def get_value_from_redis(key):
    try:   
          value = r.get(key)  
          return value
    
    except:
         print("Issue on getting key from redis .. ")

#set key value in redis
def set_value_in_redis(key,value):
    try:   
          r.set(key,value)

    except:
         print("Issue on set key in redis .. ")


# Parse the JSON response
content = bytes_data.content
json_string = content.decode('utf-8')
response_data = json.loads(json_string)

#check for previous data in redis
previous_data = check_previous_data_existance()

# Initialize an empty dictionary to store the results
results = {}
percentage_result = {}

# Extract values from the buckets
buckets = response_data['aggregations']['top_organizations']['buckets']

if(previous_data == Result.Ok):
    for bucket in buckets:
        key = bucket['key']
        if(not key) : 
            continue
        doc_count = bucket['doc_count']
        #results[key] = doc_count

        previous = get_value_from_redis(key)
        percent = (int(doc_count) / int(previous)) * 100 

        results[key] = percent

        #update value in redis
        set_value_in_redis(key , doc_count)


elif(previous_data == Result.Empty):
    for bucket in buckets:
        key = bucket['key']
        if(not key) : 
            continue
        doc_count = bucket['doc_count']
       
        #update value in redis
        set_value_in_redis(key , doc_count)


elif(previous_data == Result.Error):
    print("Error occured while trying to check redis..")
    gauge_metric.set(0)





#threshold
if(previous_data == Result.Ok):
    gauge_metric.set(1)

    for key, value in results.items():
        if(key == "Mobile Communication Company of Iran PLC"):
            if(value < 75):
                send_message(key,value)

        if(key == "Iran Cell Service and Communication Company"):
            if(value < 75):
                send_message(key,value)

        if(key == "Iran Telecommunication Company PJS"):
            if(value < 75):
                send_message(key,value)

        if(key == "Rightel Communication Service Company PJS"):
            if(value < 75):
                send_message(key,value)


# prometheus - pushgateway
# Specify the address of the Pushgateway
pushgateway_address = 'http://<pushgateway_ip:port>'
# Push the metrics to the Pushgateway
push_to_gateway(pushgateway_address, job='app_healthcheck', registry=registry)
