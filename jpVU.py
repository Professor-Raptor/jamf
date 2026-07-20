
#              _____                    _____                        _____                    _____          
#             /\    \                  /\    \                      /\    \                  /\    \         
#            /::\    \                /::\    \                    /::\____\                /::\____\        
#            \:::\    \              /::::\    \                  /:::/    /               /:::/    /        
#             \:::\    \            /::::::\    \                /:::/    /               /:::/    /         
#              \:::\    \          /:::/\:::\    \              /:::/    /               /:::/    /          
#               \:::\    \        /:::/__\:::\    \            /:::/____/               /:::/    /           
#               /::::\    \      /::::\   \:::\    \           |::|    |               /:::/    /            
#      _____   /::::::\    \    /::::::\   \:::\    \          |::|    |     _____    /:::/    /      _____  
#     /\    \ /:::/\:::\    \  /:::/\:::\   \:::\____\         |::|    |    /\    \  /:::/____/      /\    \ 
#    /::\    /:::/  \:::\____\/:::/  \:::\   \:::|    |        |::|    |   /::\____\|:::|    /      /::\____\
#    \:::\  /:::/    \::/    /\::/    \:::\  /:::|____|        |::|    |  /:::/    /|:::|____\     /:::/    /
#     \:::\/:::/    / \/____/  \/_____/\:::\/:::/    /         |::|    | /:::/    /  \:::\    \   /:::/    / 
#      \::::::/    /                    \::::::/    /          |::|____|/:::/    /    \:::\    \ /:::/    /  
#       \::::/    /                      \::::/    /           |:::::::::::/    /      \:::\    /:::/    /   
#        \::/    /                        \::/____/            \::::::::::/____/        \:::\__/:::/    /    
#         \/____/                          ~~                   ~~~~~~~~~~               \::::::::/    /     
#                                                                                         \::::::/    /      
#                                                                                          \::::/    /       
#                                                                                           \::/____/        
#                                                                                            ~~              
#       Jamf Pro VPP Updater       
#       JP.VU  v1.7
#       Professor Raptor
#
#
#
#   This script is for pushing scheduled app updates to mobile devices via Jamf API.
#   It does this by:  waits until scheduled time (and waits inbetween most of these steps) > send restart command to 
#       devices > change app setting to force updates > send INSTALLED_APPLICATION_LIST command to devices > send 
#       blank push to devices > revert app setting 
#   In its current configuration it only updates one app (appid) for devices in one static group (groupid), but it  
#       can easily be reconfigured by modifying the big try statement at the bottom. 
#
#   Warning: Curretly it sends a request for EVERY DEVICE in the static group to retrieve info due to a bug with one 
#                of the endpoints. Known issue: PI119893 


server = "https://SERVER.jamfcloud.com"
appid = "1"
groupid = "1"


# Get your client_secret here or when it is first needed (you can search for the line before the big try statement). 
# If you want to use pbencrypt, leave it as None and set pbtoken and password_hash here instead. 
client_id = ''
client_secret = None
pbtoken = ''
password_hash = ''

#   Target time must be after midnight
default_target_time = "02:00"



#=====================================================================================================================

if client_secret is None:
    import pbencrypt
import traceback
import requests
import json
import os
import time
import hashlib
import random
from getpass import getpass
from datetime import datetime, timedelta

class style:
    cyan = '\033[38;5;51m\033[48;5;0m'
    red2 = '\033[38;5;0m\033[48;5;124m'
    error = '\033[38;5;196m\033[48;5;0m'
    orng = '\033[38;5;166m\033[48;5;0m'
    brwn = '\033[38;5;94m\033[48;5;0m'
    grey = '\033[38;5;244m\033[48;5;0m'
    green = '\033[38;5;2m\033[48;5;0m'
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
        print("  +++")
    else:
        print(style.error,"\n ERROR ACQUIRING TOKEN \n",style.endc, style.orng,response,response.text,style.endc)
        input()
        input()
        exit()
    json_response=json.loads(response.text)
    return json_response["access_token"]

def kill_token():
    global error_count
    if bearerToken != None:
        headers = {
            "Authorization": "Bearer " + bearerToken,
            "accept": "application/json"
        }
        url = server + "/api/v1/auth/invalidate-token"
        response = requests.post(url, headers=headers)
        status_code = response.status_code
        if status_code == 204:
            print("  xxx")
        else:
            print(style.error," ERROR INVALIDATING TOKEN \n",style.endc, style.orng,response,response.text,style.endc)
            # global error_count
            error_count = error_count+1
    else:
        print(style.error,"\n kill_token failed: bearerToken not set",style.endc)
        # global error_count
        error_count = error_count+1

def send_command(device_list,command):
    clientdata = [{'managementId':device['managementId']} for device in device_list]
    # deviceids = [device['mobileDeviceId'] for device in device_list]
    deviceids = [device['id'] for device in device_list]
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json"
    }
    payload = {
        "clientData": clientdata,
        "commandData": { "commandType": command }
    }
    url = server + "/api/v2/mdm/commands"
    response = requests.post(url, json=payload, headers=headers)
    status_code = response.status_code
    if status_code == 201:
        print('',command,"COMMANDS CREATED:\n",style.grey,deviceids,style.endc)
    else:
        print(style.error,"ERROR CREATING COMMANDS:",command,style.endc, style.orng,response,response.text,style.endc)
        global error_count
        error_count = error_count+1

def send_blank_push(device_list):
    global error_count
    clientdata = [device['managementId'] for device in device_list]
    # deviceids = [device['mobileDeviceId'] for device in device_list]
    deviceids = [device['id'] for device in device_list]
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json"
    }
    payload = { "clientManagementIds": clientdata }
    url = server + "/api/v2/mdm/blank-push"
    response = requests.post(url, json=payload, headers=headers)
    status_code = response.status_code
    data = response.json()
    # if status_code == 200 and data['errorUuids'] == []:
    if status_code == 200:
        print(' BLANK PUSHES SENT:\n',style.grey,deviceids,data,style.endc)
        if len(data['errorUuids']) != 0:
            print(style.error,'ERROR SENDING BLANK PUSH:',data,style.endc)
            error_count = error_count+1
    else:
        print(style.error,'ERROR SENDING BLANK PUSHES',style.endc, style.orng,response,response.text,style.endc)
        # global error_count
        error_count = error_count+1



#   Changes "Force Update" setting for app. Setting should be "true" or "false"
def update_setting(appid, setting):
    payload = """<?xml version="1.0" encoding="UTF-8"?><mobile_device_application><general>
    <keep_app_updated_on_devices>""" + setting + """</keep_app_updated_on_devices>
    </general></mobile_device_application>"""
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "text/xml"
    }
    url = server + "/JSSResource/mobiledeviceapplications/id/"
    response = requests.put(url+appid, data=payload, headers=headers)
    status_code = response.status_code
    if status_code == 201:
        print(" UPDATE SETTING PUT TO: "+setting)
    else:
        print(style.error,"\n ERROR PUTTING UPDATE SETTING \n",style.endc, style.orng,response,response.text,style.endc)
        kill_token()
        input()
        input()
        exit()

#   Get device list from static device group
# def old_get_device_list():
    # headers = {
        # "Authorization": "Bearer " + bearerToken,
        # "accept": "application/json"
    # }
    # url = server + "/JSSResource/mobiledevicegroups/id/9"
    # response = requests.get(url, headers=headers)
    # status_code = response.status_code
    # if status_code == 200:
        # print(" DEVICE GROUP INFO RECEIVED ")
    # else:
        # print(style.error,"\n ERROR GETTING DEVICE GROUP FOR LIST \n",style.endc, style.orng,response,response.text,style.endc)
        # kill_token()
        # input()
        # input()
        # exit()
    # json_response=json.loads(response.text)
    # return json_response["mobile_device_group"]["mobile_devices"]

def get_device_list(list_id):
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json"
    }
    url = server + f"/api/v2/mobile-device-groups/static-group-membership/{list_id}?page=0&page-size=100&sort=displayName%3Aasc"
    response = requests.get(url, headers=headers)
    status_code = response.status_code
    if status_code == 200:
        print(" DEVICE GROUP INFO RECEIVED ")
    else:
        print(style.error,"\n ERROR GETTING DEVICE GROUP FOR LIST \n",style.endc, style.orng,response,response.text,style.endc)
        kill_token()
        input()
        input()
        exit()
    json_response=json.loads(response.text)
    return json_response["results"]

def get_device_info(device_id):
    headers = {
        "Authorization": "Bearer " + bearerToken,
        "accept": "application/json"
    }
    url = server + "/api/v2/mobile-devices/"
    response = requests.get(url+device_id, headers=headers)
    status_code = response.status_code
    if status_code != 200:
        print(style.error,'ERROR GETTING DEVICE INFO:',device_id,style.endc, style.orng,response,response.text,style.endc)
    return json.loads(response.text)


#   For improved readability later
def print_DTs():
    print(style.brwn,datetime.now(),style.endc, "\n SLEEPING \n", sep="")
def print_DTr():
    print("\n", style.brwn,datetime.now(),style.endc, sep="")

#--------------------------------------------------------------------------------------------

os.system('title JP.VU')
error_count = 0
completion_check = 0

#   Password prompt
if client_secret is None:
    i1 = 0
    while 0==0:
        if i1 == 1:
            print("\n INCORRECT PASSWORD \n Enter to try again")
            input()
        i1 = 1
        os.system('cls')
        print("\n\n   -------------\n"+style.cyan+"       JP.VU \n"+style.endc+"   -------------\n\n")
        print("\n\n Password \n")
        password = getpass(">")
        if pbencrypt.vhash(password_hash, password):
            break

#   Scope prompt
i1 = 0
while 0==0:
    if i1 == 1:
        print("\n INVALID ENTRY \n Enter to try again")
        input()
    i1 = 1
    os.system('cls')
    print("\n\n   -------------\n"+style.cyan+"       JP.VU \n"+style.endc+"   -------------\n\n")
    print("\n Scope all devices: {Enter} \n Scope specific devices: {ID},{ID}... \n Scope random devices: R, {quantity} \n")
    try:
        response = input(">").split(',')
        if response[0] == '':
            scope = 'all'
            break
        elif response[0].lower() == 'r':
            scope = 'rand'
            random_scope = int(response[1])
            break
        else: 
            scope = 'select'
            select_scope = response
            break
    except:
        pass

#   Target time prompt
hour, minute = default_target_time.split(":")
tim = datetime.now() + timedelta(days=1)
tim = tim.replace(hour=int(hour),minute=int(minute),second=0,microsecond=0)
i1 = 0
response = None
while response != "":
    os.system('cls')
    print("\n\n   -------------\n"+style.cyan+"       JP.VU \n"+style.endc+"   -------------\n\n")
    if i1 != 0:
        tim = datetime.strptime(response, "%Y-%m-%d %H%M")
    i1 = 1
    delta = tim - datetime.now().replace(microsecond=0)
    target = tim.strftime("%Y-%m-%d %H%M")
    print(" Script will run at:\n\n", target, "\n Delta:", delta)
    print("\n Enter to continue or input new target.\n")
    response = input(">")


#   Sleeping until target time and timecheck
os.system('cls')
print("\n\n   -------------\n"+style.cyan+"       JP.VU \n"+style.endc+"   -------------\n\n")
if scope == 'all':
    print(" SCOPE: ALL ")
elif scope == 'rand':
    print(" SCOPE: RANDOM >", random_scope)
elif scope == 'select':
    print(" SCOPE: SELECTED >", select_scope)
delta = tim - datetime.now().replace(microsecond=0)
print("\n SLEEPING UNTIL:\n", target, "\n DELTA:", delta)
print("\n", style.brwn,datetime.now(),style.endc, "\n SLEEPING \n\n", sep="")

time.sleep(delta.total_seconds())
if datetime.now().timestamp() < (tim.timestamp() - 600) or datetime.now().timestamp() > (tim.timestamp() + 600):
    print(style.error,"\n ERROR: CURRENT TIME OUTSIDE BOUNDS OF TARGET TIME ",style.endc, style.orng,"\n now:",datetime.now(), "\n tim:",tim,style.endc)
    input()
    input()
    exit()

# client_secret = None
if client_secret is None:
    client_secret = pbencrypt.decrypt(pbtoken, password).decode()
bearerToken = None

try:
    print_DTr()
    bearerToken = get_token()
    device_list = get_device_list(groupid)
    
    #   This bullshit is here because the new endpoint for retrieving devices from a static group returns with most 
    #       of the values as None, including the Management ID. Known issue: PI119893 
    #   This workaround requies sending a request for EVERY DEVICE to get the Management IDs. 
    #   Several lines of code are commented and replaced because the endpoint for getting device info returns 
    #       'id' instead of 'mobileDeviceId'. 
    device_list = [get_device_info(device['mobileDeviceId']) for device in device_list]
    
    if scope == 'rand':
        random.shuffle(device_list)
        device_list = device_list[:random_scope]
    elif scope == 'select':
        # device_list = [device for device in device_list if device['mobileDeviceId'] in select_scope]
        device_list = [device for device in device_list if device['id'] in select_scope]
    time.sleep(10)
    send_command(device_list,'RESTART_DEVICE')
    kill_token()
    print_DTs();time.sleep(10*60);print_DTr()
    
    bearerToken = get_token()
    update_setting(appid,"true")
    kill_token()
    print_DTs();time.sleep(10*60);print_DTr()
    
    bearerToken = get_token()
    send_command(device_list,'INSTALLED_APPLICATION_LIST')
    time.sleep(10)
    send_blank_push(device_list)
    kill_token()
    print_DTs();time.sleep(60*60);print_DTr()
    
    bearerToken = get_token()
    update_setting(appid,"false")
    completion_check = 1
    
except Exception:
    traceback.print_exc()
finally:
    kill_token()
    
    print(style.brwn,datetime.now(),style.endc, sep="")
    client_secret = None
    password = None
    print("\n\n")
    if error_count == 0:
        print(style.green+"   ERRORS: 0"+style.endc)
    else:
        print(style.error+"   ERRORS: "+str(error_count)+style.endc)
    if completion_check == 1:
        print(style.green+"   COMPLETE: YES"+style.endc)
    else:
        print(style.error+"   COMPLETE: NO"+style.endc)
    if error_count == 0 and completion_check == 1:
        print("\n   -------------\n"+style.cyan+"       JP.VU \n"+style.endc+"   -------------\n\n\n\n")
    else:
        print("\n   "+style.red2+"-------------"+style.endc+"\n   "+style.red2+"    JP.VU    "+style.endc+"\n   "+style.red2+"-------------"+style.endc+"\n\n\n\n")
    input()
    input()
