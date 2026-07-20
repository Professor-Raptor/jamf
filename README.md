# jamf
Python scripts for Jamf Pro automation, including scheduled mobile app updates.  

## pbencrypt
Quick note, [pbencrypt](https://github.com/Professor-Raptor/pbencrypt) is a cryptography wrapper that was made to satisfy a weird requirement in our company. For these scripts, it is used to allow you to store your api client secret in the script as an encrypted string which is decrypted with a user provided password. It is completely optional; you can instead just store your secret in environment variables or however you want to do it.  

## jpVU
jpVU is for is for pushing scheduled app updates to mobile devices. The intent is to start this script before you leave and it will push the updates overnight to the devices you scope (all in the static group, by ID, or a random quantity) at the time you select. In our company we have an app that we strictly cannot allow automatic updates for which lead to the creation of this.  
\
It requires the python requests library (pip install requests) and I have the API role setup with these privileges but they may not all be required:  
```
Send Device Information Command, Create Mobile Devices, View MDM command information in Jamf Pro API, Read Mobile Devices, Read Static Mobile Device Groups, Send Mobile Device Restart Device Command, Send MDM Check In Command, Read Mobile Device Applications, Send Inventory Requests to Mobile Devices, Send Blank Pushes to Mobile Devices, Update Mobile Device Applications, Send MDM command information in Jamf Pro API
```
<img width="587" height="1036" alt="jpvu_demo_screenshot" src="https://github.com/user-attachments/assets/27e212b9-38dd-4594-9962-323767aa7248" />

## jpCI
jpCI is for our custom return-to-service procedure, reinstalling specific apps on specific devices, etc. It is more specialized for our use case but perhaps you can modify it for use in your own company. 
