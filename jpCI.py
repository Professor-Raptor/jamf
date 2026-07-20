
#              _____                    _____                            _____                    _____          
#             /\    \                  /\    \                          /\    \                  /\    \         
#            /::\    \                /::\    \                        /::\    \                /::\    \        
#            \:::\    \              /::::\    \                      /::::\    \               \:::\    \       
#             \:::\    \            /::::::\    \                    /::::::\    \               \:::\    \      
#              \:::\    \          /:::/\:::\    \                  /:::/\:::\    \               \:::\    \     
#               \:::\    \        /:::/__\:::\    \                /:::/  \:::\    \               \:::\    \    
#               /::::\    \      /::::\   \:::\    \              /:::/    \:::\    \              /::::\    \   
#      _____   /::::::\    \    /::::::\   \:::\    \            /:::/    / \:::\    \    ____    /::::::\    \  
#     /\    \ /:::/\:::\    \  /:::/\:::\   \:::\____\          /:::/    /   \:::\    \  /\   \  /:::/\:::\    \ 
#    /::\    /:::/  \:::\____\/:::/  \:::\   \:::|    |        /:::/____/     \:::\____\/::\   \/:::/  \:::\____\
#    \:::\  /:::/    \::/    /\::/    \:::\  /:::|____|        \:::\    \      \::/    /\:::\  /:::/    \::/    /
#     \:::\/:::/    / \/____/  \/_____/\:::\/:::/    /          \:::\    \      \/____/  \:::\/:::/    / \/____/ 
#      \::::::/    /                    \::::::/    /            \:::\    \               \::::::/    /          
#       \::::/    /                      \::::/    /              \:::\    \               \::::/____/           
#        \::/    /                        \::/____/                \:::\    \               \:::\    \           
#         \/____/                          ~~                       \:::\    \               \:::\    \          
#                                                                    \:::\    \               \:::\    \         
#                                                                     \:::\____\               \:::\____\        
#                                                                      \::/    /                \::/    /        
#                                                                       \/____/                  \/____/         
#       Jamf Pro Command Interface
#       JP.CI  v1.4
#       Professor Raptor
#
#
#
#   This script is for automating Jamf workflows such as single-device app reinstalls and custom return to service.
#   You will need to adapt it to your org/use-case. Start with modifying set_name_and_tag, c_add_to_all_groups,  
#       c_target, and the main loop at the bottom. 


server = "https://SERVER.jamfcloud.com"



# Get your client_secret here or when it is first needed (you can search for the line before the big try statement). 
# If you want to use pbencrypt, leave it as None and set pbtoken and password_hash here instead. 
client_id = ''
client_secret = None
pbtoken = ''
password_hash = ''




#=====================================================================================================================

if client_secret is None:
    import pbencrypt
import traceback
import requests
import json
import os
import hashlib
from getpass import getpass
import pyperclip


class style:
    cyan = '\033[38;5;51m\033[48;5;0m'
    error = '\033[38;5;196m\033[48;5;0m'
    orng = '\033[38;5;166m\033[48;5;0m'
    brwn = '\033[38;5;94m\033[48;5;0m'
    grey = '\033[38;5;244m\033[48;5;0m'
    green = '\033[38;5;2m\033[48;5;0m'
    yellow = '\033[38;5;226m\033[48;5;0m'
    ul = '\033[4m'
    endc = '\033[0m'

def get_token():
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded"
    }
    url = server + "/api/v1/oauth/token"
    response = requests.post(url, data=payload, headers=headers)
    status_code = response.status_code
    if status_code == 200:
        print(style.grey,'  +++',style.endc)
    else:
        print(style.error,'\n ERROR ACQUIRING TOKEN \n',style.endc, style.orng,response,response.text,style.endc)
        input()
    json_response=json.loads(response.text)
    return json_response['access_token']

def kill_token(bearerToken):
    if bearerToken != None:
        headers = {
            "Authorization": "Bearer " + bearerToken,
            "accept": "application/json"
        }
        url = server + "/api/v1/auth/invalidate-token"
        response = requests.post(url, headers=headers)
        status_code = response.status_code
        if status_code == 204:
            print(style.grey,'  xxx',style.endc)
        else:
            print(style.error,' ERROR INVALIDATING TOKEN \n',style.endc, style.orng,response,response.text,style.endc)
    else:
        print(style.error,'\n kill_token failed: bearerToken not set',style.endc)

def send_restart(bearerToken,device_id,target_manid):
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json"
    }
    payload = {
        "clientData": [{ "managementId": target_manid }],
        "commandData": { "commandType": "RESTART_DEVICE" }
    }
    url = server + "/api/v2/mdm/commands"
    response = requests.post(url, json=payload, headers=headers)
    status_code = response.status_code
    if status_code == 201:
        print('RESTART COMMAND CREATED:',device_id)
    else:
        print(style.error,'ERROR CREATING RESTART COMMAND:',device_id,style.endc, style.orng,response,response.text,style.endc)

def send_blank_push(bearerToken,device_id,target_manid):
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json"
    }
    payload = {
        "clientManagementIds": [ target_manid ]
    }
    url = server + "/api/v2/mdm/blank-push"
    response = requests.post(url, json=payload, headers=headers)
    status_code = response.status_code
    data = response.json()
    print(data)
    if status_code == 200 and data['errorUuids'] == []:
        print('BLANK PUSH SENT:',device_id)
    else:
        print(style.error,'ERROR SENDING BLANK PUSH:',device_id,style.endc, style.orng,response,response.text,style.endc)

def get_device_info(bearerToken,device_id):
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json"
    }
    url = server + "/api/v2/mobile-devices/"
    response = requests.get(url+device_id, headers=headers)
    status_code = response.status_code
    if status_code != 200:
        print(style.error,'ERROR GETTING DEVICE INFO:',device_id,style.endc, style.orng,response,response.text,style.endc)
        input()
    return json.loads(response.text)

def set_name_and_tag(bearerToken,device_id):
    asset_tag = int(device_id)
    payload = {
        "name": "ID-"+str(asset_tag),
        "assetTag": str(asset_tag)
    }
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json",
        "content-type": "application/json"
    }
    url = server + "/api/v2/mobile-devices/"
    response = requests.patch(url+device_id, json=payload, headers=headers)
    status_code = response.status_code
    if status_code == 200:
        print('DEVICE NAME AND ASSET TAG SET:',device_id)
    else:
        print(style.error,'\n ERROR SETTING NAME AND TAG \n',style.endc, style.orng,response,response.text,style.endc)

def set_group_membership(bearerToken,group_id,group_name,device_id,setting):
    payload = {
        "groupName": group_name,
        "siteId": "-1",
        "assignments": [
            {
                "mobileDeviceId": device_id,
                "selected": setting
            }
        ]
    }
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json",
        "content-type": "application/json"
    }
    url = server + "/api/v1/mobile-device-groups/static-groups/"
    response = requests.patch(url+group_id, json=payload, headers=headers)
    status_code = response.status_code
    if status_code == 200:
        if setting == True:
            print('DEVICE',device_id,'ADDED TO GROUP',group_id+': '+group_name)
        elif setting == False:
            print('DEVICE',device_id,'REMOVED FROM GROUP',group_id+': '+group_name)
    else:
        print(style.error,'\n ERROR SETTING GROUP MEMBERSHIP \n',style.endc, style.orng,response,response.text,style.endc)

def erase_device(bearerToken,device_id):
    payload = {
        "preserveDataPlan": True,
        "disallowProximitySetup": False,
        "clearActivationLock": True
    }
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json",
        "content-type": "application/json"
    }
    url = server + "/api/v2/mobile-devices/"+device_id+"/erase"
    response = requests.post(url, json=payload, headers=headers)
    status_code = response.status_code
    if status_code == 200:
        print('ERASE COMMAND CREATED:',device_id)
    else:
        print(style.error,'\n ERROR CREATING ERASE COMMAND \n',style.endc, style.orng,response,response.text,style.endc)

#--------------------------------------------------------------------------------------------

def c_push(target_device,target_manid):
    try:
        bearerToken = get_token()
        send_blank_push(bearerToken,target_device,target_manid)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)

def c_restart(target_device,target_manid):
    try:
        bearerToken = get_token()
        send_restart(bearerToken,target_device,target_manid)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)

#   Should only be tested overnight
def c_reinstall(target_device,target_manid,group_id,group_name):
    input(f'enter to uninstall {group_name}')
    try:
        bearerToken = get_token()
        set_group_membership(bearerToken,group_id,group_name,target_device,False)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)
    input('enter to restart')
    c_restart(target_device,target_manid)
    input(f'enter to install {group_name}')
    try:
        bearerToken = get_token()
        set_group_membership(bearerToken,group_id,group_name,target_device,True)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)

def c_add_to_all_groups(target_device):
    try:
        bearerToken = get_token()
        set_group_membership(bearerToken,'1','MAIN',target_device,True)
        set_group_membership(bearerToken,'2','SOMETHING',target_device,True)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)

def c_name(target_device):
    try:
        bearerToken = get_token()
        set_name_and_tag(bearerToken,target_device)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)

def c_erase(target_device):
    input('enter to erase device')
    try:
        bearerToken = get_token()
        erase_device(bearerToken,target_device)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)

def c_details(target_device):
    try:
        bearerToken = get_token()
        return get_device_info(bearerToken,target_device)
    except Exception:
        traceback.print_exc()
    finally:
        kill_token(bearerToken)


#--------------------------------------------------------------------------------------------
help_info='''
Type the command or the capitalized letter(s) to execute a command. 

Target: Scope a device by ID or asset tag to be interacted with.
Inventory: Sends an update inventory command to device.
Restart: Sends a restart command to device.
APP regroup: Use to reinstall the configed app. This will:
             remove the device from the app group > restart the
             device > add the device to the app group.
Group: Adds device to all (primary) device groups.
Name: Changes device name and asset tag to match schema.
Erase: Wipes device and removes activation lock. For return to service, 
       use the Name and Group commands after the device has reset.
Details: Dumps device info. 
exit: You can probably guess.
'''
#--------------------------------------------------------------------------------------------

os.system('title JP.CI')

#   Password prompt
if client_secret is None:
    i1 = 0
    while 0==0:
        if i1 == 1:
            print('\n INCORRECT PASSWORD \n Enter to try again')
            input()
        i1 = 1
        os.system('cls')
        print('\n\n   -------------\n'+style.cyan+'       JP.CI \n'+style.endc+'   -------------\n\n\n')
        password = getpass(' Password>')
        if pbencrypt.vhash(password_hash, password):
            break
if client_secret is None:
    client_secret = pbencrypt.decrypt(pbtoken, password).decode()

#   Main
def c_target():
    os.system('cls')
    print('\n\n   -------------\n'+style.cyan+'       JP.CI \n'+style.endc+'   -------------\n\n\n')
    target_device = input(' Target>')
    device_info = c_details(target_device)
    target_manid = device_info['managementId']
    pyperclip.copy(device_info['serialNumber'])
    os.system('cls')
    print('\n\n   -------------\n'+style.cyan+'       JP.CI \n'+style.endc+'   -------------\n\n')
    print(style.orng+' Target:  '+str(device_info['id'])+' '+str(device_info['name'])+'    '+str(device_info['username'])+style.endc+'\n')
    
    # print('   '+style.orng+'T'+style.endc+'arget ')
    # print('   '+style.orng+'R'+style.endc+'estart ')
    print('   Target ')
    print('   Push ')
    print('   Restart ')
    print('   APP regroup ')
    print('   Group ')
    print('   Name ')
    print('   Erase ')
    print('   Details ')
    print('   Help ')
    print('')
    return target_device, target_manid
target_device, target_manid = c_target()

#--------------------------------------------------------------------------------------------

command = None
while 0==0:
    print(style.orng)
    command = input('>').lower()
    print(style.endc)
    if command in {'t','target'}:
        target_device, target_manid = c_target()
    elif command in {'p','push'}:
        c_push(target_device,target_manid)
    elif command in {'r','restart'}:
        c_restart(target_device,target_manid)
    elif command in {'ap','app','app regroup'}:
        c_reinstall(target_device,target_manid,'1','SOMETHING')
    elif command in {'g','group'}:
        c_add_to_all_groups(target_device)
    elif command in {'n','name'}:
        c_name(target_device)
    elif command in {'e','erase'}:
        c_erase(target_device)
    elif command in {'d','details'}:
        print(c_details(target_device))
    elif command in {'h','help'}:
        print(help_info)
    elif command == 'exit':
        exit()
    else:
        print(' Invalid command')
    print('')



