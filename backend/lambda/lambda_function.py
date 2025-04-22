import json
import requests

def lambda_handler(event, context):
    for record in event['Records']:
        process_message(record)
    print("done")

def process_message(record):
    try:
        if record.get('Event') == 's3:TestEvent':
            print('Test event received, no action taken.')
            return
        
        body = record.get('body')
        if not body:
            print('No body found in the record.')
            return

        body_json = json.loads(body)

        if body_json.get("Event") == "s3:TestEvent":
            print('Test event received, no action taken.')
            return

        records = body_json.get('Records')
        if not records:
            print('No S3 data found in the record.')
            return

        for s3_record in records:
            if 's3' not in s3_record:
                print('No S3 data found in the S3 record.')
                continue

            bucket_name = s3_record['s3']['bucket']['name']
            object_key = s3_record['s3']['object']['key']

            
            s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"

            payload = {
                "url": s3_url
            }

            api_endpoint = "http://ollama:8000/api/s3_event"
            
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(api_endpoint, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                print('Request successful!')
            else:
                print(f"Request failed: {response.text}")
    
    except Exception as err:
        print(f"An error occurred: {err}")
        raise err
