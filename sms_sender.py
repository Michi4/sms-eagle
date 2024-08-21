import csv
import time
import json
import sys
from twilio.rest import Client

def load_config():
    with open('config.json', 'r') as file:
        return json.load(file)

def get_job_by_id(job_id):
    config = load_config()
    for job in config['jobs']:
        if job['id'] == job_id:
            return job
    return None

def update_config(job_id, successful_numbers, failed_numbers):
    with open('config.json', 'r') as file:
        config = json.load(file)

    for job in config['jobs']:
        if job['id'] == job_id:
            job['successful_numbers'] = list(set(job.get('successful_numbers', []) + successful_numbers))
            job['failed_numbers'] = list(set(failed_numbers))
            break

    with open('config.json', 'w') as file:
        json.dump(config, file, indent=4)

def send_bulk_sms(account_sid, auth_token, from_number, message, phone_numbers, job_id, timeout_seconds=2):
    client = Client(account_sid, auth_token)
    successful_numbers = []
    failed_numbers = []

    for num in phone_numbers:
        try:
            print(f"Sending to {num}")
            client.messages.create(to=num, from_=from_number, body=message)
            successful_numbers.append(num)
        except Exception as e:
            print(f"Failed to send SMS to {num}: {e}")
            failed_numbers.append(num)
        finally:
            time.sleep(timeout_seconds)  # Rate limiting

    # Update config with the results
    update_config(job_id, successful_numbers, failed_numbers)

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
