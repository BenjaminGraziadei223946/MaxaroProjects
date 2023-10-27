from azure.communication.callautomation import (CallAutomationClient)

# Your unique Azure Communication service endpoint
endpoint_url = 'endpoint=https://maxcomser.europe.communication.azure.com/;accesskey=sOLSdBBHU9tgsPa1QQ779r73xsz5S5U3T6+QSejGzItpTep2T1cz0cadvSJQNqz5lyWS2QicoGYXVnD5dhq91w=='
client = CallAutomationClient.from_connection_string(endpoint_url)

from azure.communication.callautomation import (
    CallAutomationClient,
    CallInvite,
    CommunicationUserIdentifier,
    UnknownIdentifier,
    MicrosoftTeamsUserIdentifier,
    )
# target endpoint for ACS User
teams_id = MicrosoftTeamsUserIdentifier("bgraziadei@maxaro.nl")

# make invitation
call_invite = CallInvite(target=teams_id)

# callback url to receive callback events
callback_url = "https://eventscallback.azurewebsites.net"

# send out the invitation, creating call
result = client.create_call(call_invite, callback_url)

# this id can be used to do further actions in the call
call_connection_id = result.call_connection_id

# using call connection id, get call connection
call_connection = client.get_call_connection(call_connection_id)

# from callconnection of result above, play media to all participants
#my_file = FileSource(url="https://<FILE-SOURCE>/<SOME-FILE>.wav")
#call_connection.play_to_all(my_file)