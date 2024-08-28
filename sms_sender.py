import csv
import time
import json
import sys
import uuid

import requests


def load_config():
    with open('config.json', 'r') as file:
        return json.load(file)


def get_job_by_id(job_id):
    config = load_config()
    for job in config['jobs']:
        if job['id'] == job_id:
            return job
    return None


def update_config(job_id, is_successful, successful_sms, error_message=""):
    with open('config.json', 'r') as file:
        config = json.load(file)

    for job in config['jobs']:
        if job['id'] == job_id and is_successful:
            job['is_finished'] = True
            job['is_scheduled'] = False
            job['successful_sms'] = successful_sms
            job['failed_sms'] = []
            break
        elif not is_successful:
            job['is_finished'] = True
            job['is_scheduled'] = False
            job['failed_sms'] = successful_sms
            job['error_message'] = error_message

    with open('config.json', 'w') as file:
        json.dump(config, file, indent=4)


def send_bulk_sms(target_device_iden, access_token, phone_numbers, message, job_id):
    headers = {
        'Access-Token': access_token,
        'Content-Type': 'application/json'
    }

    data_payload = {
        "data": {
            "addresses": phone_numbers,
            "file_type": "text/plain",
            "guid": str(uuid.uuid4()),
            "message": message,
            "target_device_iden": target_device_iden
        },
    }

    response = requests.post(
        url='https://api.pushbullet.com/v2/texts',
        headers=headers,
        json=data_payload
    )
    response_data = response.json()
    if response.status_code == 200:
        if response_data.get('active') and response_data.get('iden'):
            print("Message sent successfully!")
            update_config(job_id, True, phone_numbers)
    else:
        print("Failed to confirm message sending:", response_data)
        update_config(job_id, False, phone_numbers, response_data.get('error_code'))


def main(job_id):
    config = load_config()
    sms_sender = config['sms_sender']
    job = get_job_by_id(job_id)

    if not job:
        print(f"Job with ID {job_id} not found.")
        sys.exit(1)

    # Load the SMS message from file
    with open(job['message_file'], 'r') as message_file:
        message = message_file.read().strip()

    if len(message) == 0:
        print(f"SMS message in {job['message_file']} is empty. Exiting!")
        sys.exit(1)

    # Load phone numbers from CSV
    with open(job['csv_path'], 'r') as csvfile:
        numbers = set([row[0].strip() for row in csv.reader(csvfile) if row[0].strip()])

    # Calculate message segments and total cost
    SMS_LENGTH = 160
    segments = (len(message.encode('utf-8')) // SMS_LENGTH) + 1
    MSG_COST = 0.0979
    cost = MSG_COST * segments * len(numbers)

    print(f"> Sending {len(numbers)} messages of {segments} segments each, at a cost of ${cost:.2f}.")
    
    confirm = input("Send these messages? [Y/n] ").strip().lower()
    if confirm != 'y':
        print("Exiting without sending messages.")
        sys.exit(0)

    # Send the SMS messages
    send_bulk_sms(sms_sender['account_sid'], sms_sender['auth_token'], sms_sender['from_number'], message, numbers, job_id)

    print("All SMS processing complete.")

if __name__ == "__main__":
    job_id = 1  # You can change this to run different jobs
    main(job_id)
