***To start the server go to the server directory and run the server.py***

server will be hosted at 127.0.0.1:5000/

it includes the login page and the graph page where we can see patient health

username = admin
password = 12345


change username and password to connect to the mongodb server

add your credentials of twilio acc to send the sms



# add OM2M server also
link: -  "https://www.eclipse.org/downloads/download.php?file=/om2m/releases/1.4.1/eclipse-om2m-v1-4-1.zip"

change port to 5089
start the server

create basic request to create a AE collection
OM2M_URL = "http://localhost:5089/~/in-cse/in-name"  # Change to your OM2M server address
HEADERS_AE = {
    "X-M2M-Origin": "Cadmin",
    "X-M2M-RI": "12345",
    "Content-Type": "application/json;ty=2"
}

ae_payload = {
    "m2m:ae": {
        "rn": "PATIENT_DATA",
        "api": "app.patient.health",
        "rr": True
    }
}
res1 = requests.post(OM2M_URL, headers=HEADERS_AE, data=json.dumps(ae_payload))
print("AE Response:", res1.status_code, res1.text)


# use cpp file for esp32