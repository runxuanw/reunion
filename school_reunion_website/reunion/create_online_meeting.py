"""Create meeting link."""
import json

import requests
import datetime
from msal import ConfidentialClientApplication
from .app_settings import CLIENT_CREDENTIAL, REUNION_CLIENT_ID, TENANT_NAME, ADMIN_USER_OBJECT_ID

# Make this as a module level variable, so token will be cached.
APP = ConfidentialClientApplication(client_id=REUNION_CLIENT_ID,
                                    authority=f"https://login.microsoftonline.com/{TENANT_NAME}",
                                    client_credential=CLIENT_CREDENTIAL)


def create_meeting_link(meeting_name, start_time, end_time):
    """start and end time is default to UTC timezone."""
    result = APP.acquire_token_silent(scopes=["https://graph.microsoft.com/.default"], account=None)
    if not result:
        print("No suitable token exists in cache. Let's get a new one from AAD.")
        result = APP.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    token = result.get("access_token")
    if token is None:
        print(result.get("error"))
        print(result.get("error_description"))
        return

    payload = {
        "startDateTime": start_time.isoformat(timespec="microseconds"),
        # must in the format of "2022-03-12T14:30:34.2444915-07:00",
        "endDateTime": end_time.isoformat(timespec="microseconds"),
        "subject": meeting_name
    }
    headers_dict = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    resp = requests.post(f"https://graph.microsoft.com/v1.0/users/{ADMIN_USER_OBJECT_ID}/onlineMeetings/",
                         data=json.dumps(payload), headers=headers_dict)
    if resp.status_code != 201:
        print(f"====debug {resp.status_code} {resp.content}\n")
        print(payload)
        return
    return json.loads(resp.content).get("joinWebUrl").split("?")[0]


def main():
    print(create_meeting_link("sample meeting",
                              datetime.datetime(2022, 2, 28, 12, 0, tzinfo=datetime.timezone.utc),
                              datetime.datetime(2022, 2, 28, 13, 0, tzinfo=datetime.timezone.utc)))


if __name__ == '__main__':
    main()
