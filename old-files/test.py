import requests

url = "https://api.apollo.io/api/v1/mixed_people/api_search"

headers = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "accept": "application/json",
    "x-api-key": "l8TMBu3V3n6o8aDuENZcNA"
}

payload = {
    "organization_ids": ["5e57b09b0f85860001915922"],
    "contact_email_status": ["verified"],
    "person_titles": ["hr", "talent acquisition"], 
    "person_locations": ["chicago"],
    "page": 1,
    "per_page": 3
}

response = requests.post(url, headers=headers, json=payload)
print(response.text)