import matplotlib
matplotlib.use('Agg')
from pymongo import MongoClient
from flask import Flask, render_template, send_file, make_response, request, redirect, url_for, jsonify, json
import matplotlib.pyplot as plt
import numpy as np
import os
from bson.objectid import ObjectId
from twilio.rest import Client
import requests
import random

app = Flask(__name__)

# Ensure the 'static' directory exists
if not os.path.exists("static"):
    os.makedirs("static")

# Connect to MongoDB
client = MongoClient("mongodb+srv://username:password@cluster0.2qzfd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") # add your connection string
db = client["iot_project"]
collection = db["patients"]

# initial values to have a good scale    
co2_values = [random.randint(250, 350) for _ in range(15)]
pulse_values = [random.randint(80, 100) for _ in range(15)]
temp_values = [round(random.uniform(32, 35), 2) for _ in range(15)]
spo2_values = [round(random.uniform(96, 99), 2) for _ in range(15)]

TWILIO_ACCOUNT_SID = "" #acc sid
TWILIO_AUTH_TOKEN = ""  # auth token
TWILIO_PHONE_NUMBER = ""  # Your Twilio number
EMERGENCY_CONTACT = ""  # Number to send SMS

#fetching latest data from om2m server
def update_data(patient):
    # Get data from sensor1 (CO2, presence, emergency, temperature)
    url1 = f"http://localhost:5089/~/in-cse/in-name/PATIENT_DATA/{patient}/sensor1/la"
    headers = {
        "X-M2M-Origin": "admin:admin",
        "Accept": "application/json"
    }
    
    # Get data from sensor2 (BPM, SPO2)
    url2 = f"http://localhost:5089/~/in-cse/in-name/PATIENT_DATA/{patient}/sensor2/la"
    
    sensor1_data = None
    sensor2_data = None
    
    try:
        res1 = requests.get(url1, headers=headers)
        if res1.status_code == 200:
            data = res1.json()
            content = data["m2m:cin"]["con"]
            values = content.split(",")
            co2 = float(values[0])
            present = float(values[1])
            emergency = float(values[2])
            temp = float(values[3]) if len(values) > 3 else None  # Temperature is optional
            sensor1_data = (co2, present, emergency, temp)
        else:
            print("Failed to fetch from OM2M sensor1:", res1.status_code)
    except Exception as e:
        print("Error fetching sensor1 data:", e)
    
    try:
        res2 = requests.get(url2, headers=headers)
        if res2.status_code == 200:
            data = res2.json()
            content = data["m2m:cin"]["con"]
            values = content.split(",")
            bpm = float(values[0])
            spo2 = float(values[1])
            sensor2_data = (bpm, spo2)
        else:
            print("Failed to fetch from OM2M sensor2:", res2.status_code)
    except Exception as e:
        print("Error fetching sensor2 data:", e)
    
    return sensor1_data, sensor2_data

def generate_graphs(patient):

    sensor1_data, sensor2_data = update_data(patient)

    global co2_values, pulse_values, temp_values, spo2_values

    if sensor1_data:
        co2, present, emergency, temp = sensor1_data
        co2_values.append(co2)
        co2_values.pop(0)

        if temp is not None:
            temp_values.append(temp)
            temp_values.pop(0)

        if emergency == 1 or present == 0:
            try:
                if(present):

                    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    message = client.messages.create(
                        body=f"🚨 EMERGENCY! Patient '{patient}' needs immediate attention!",
                        from_=TWILIO_PHONE_NUMBER,
                        to=EMERGENCY_CONTACT
                    )
                    print("Emergency SMS sent:", message.sid)
                else :
                    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    message = client.messages.create(
                        body=f"🚨 EMERGENCY! Patient '{patient}' is not in the room",
                        from_=TWILIO_PHONE_NUMBER,
                        to=EMERGENCY_CONTACT
                    )
                    print("Emergency SMS sent:", message.sid)
                
            except Exception as e:
                print("Failed to send SMS:", e)

    if sensor2_data:
        bpm, spo2 = sensor2_data
        pulse_values.append(bpm)
        pulse_values.pop(0)

        spo2_values.append(spo2)
        spo2_values.pop(0)
        if bpm == -1:
            try:
                        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                        message = client.messages.create(
                            body=f"🚨 EMERGENCY! Patient '{patient}' spo2 and bpm is not correctly connected !!!",
                            from_=TWILIO_PHONE_NUMBER,
                            to=EMERGENCY_CONTACT
                        )
                        print("Emergency SMS sent:", message.sid)

                    
            except Exception as e:
                    print("Failed to send SMS:", e)

    t = np.arange(-30, 0, 2)[-15:]
    fig, axs = plt.subplots(4, 1, figsize=(6, 12))
    fig.patch.set_facecolor('#1e1e2f')  # dark background

    # Style all subplots uniformly
    for ax in axs:
        ax.set_facecolor('#2c2c3c')
        ax.tick_params(colors='white')
        ax.title.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')

    # CO2
    axs[0].plot(t, co2_values, color='#1f77b4', marker='o', label="CO2 Level")
    axs[0].set_title("Carbon Dioxide Levels (CO2)")
    axs[0].set_ylabel("PPM")
    axs[0].legend(facecolor='#2c2c3c', edgecolor='white', labelcolor='white')
    axs[0].grid(color='gray', linestyle='--', linewidth=0.5)

    # BPM
    axs[1].plot(t, pulse_values, color='#ff5733', marker='o', label="Pulse Rate")
    axs[1].set_title("Pulse Rate")
    axs[1].set_ylabel("BPM")
    axs[1].legend(facecolor='#2c2c3c', edgecolor='white', labelcolor='white')
    axs[1].grid(color='gray', linestyle='--', linewidth=0.5)

    # SPO2
    axs[2].plot(t, spo2_values, color='#9b59b6', marker='o', label="Blood Oxygen")
    axs[2].set_title("Blood Oxygen Saturation (SPO2)")
    axs[2].set_ylabel("%")
    axs[2].legend(facecolor='#2c2c3c', edgecolor='white', labelcolor='white')
    axs[2].grid(color='gray', linestyle='--', linewidth=0.5)

    # Temperature
    axs[3].plot(t, temp_values, color='#2ecc71', marker='o', label="Body Temperature")
    axs[3].set_title("Body Temperature")
    axs[3].set_ylabel("°C")
    axs[3].legend(facecolor='#2c2c3c', edgecolor='white', labelcolor='white')
    axs[3].grid(color='gray', linestyle='--', linewidth=0.5)

    plt.tight_layout()
    plt.savefig("static/graph.png", facecolor=fig.get_facecolor())
    plt.close()



# Routes
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/submit', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if username == 'admin' and password == '12345':
        return redirect(url_for('admin_dashboard'))

    test_data = collection.find_one({"name": username})
    if test_data and test_data.get("password") == password:
        return redirect(url_for('patient', patient=test_data['name']))   #sending the name as a function argument
    else:
        return redirect(url_for('home', error="Invalid credentials"))

@app.route('/admin')
def admin_dashboard():
    patients = list(collection.find())
    return render_template('admin_dashboard.html', patients=patients)

@app.route('/patient/<patient>')
def patient(patient):
    user=collection.find_one({'name': patient})

    global co2_values, pulse_values, temp_values, spo2_values
    
    # starting random data to scale the graph
    co2_values = [random.randint(250, 350) for _ in range(15)]
    pulse_values = [random.randint(80, 100) for _ in range(15)]
    temp_values = [round(random.uniform(32, 35), 2) for _ in range(15)]
    spo2_values = [round(random.uniform(96, 99), 2) for _ in range(15)]
    
    return render_template('index.html', user=user)

@app.route('/graph/<patient>')   #patient specific url added
def get_graph(patient):
    generate_graphs(patient)
    response = make_response(send_file("static/graph.png", mimetype='image/png'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/add_patient', methods=['POST'])
def add_patient():
    name = request.form['name']
    age = request.form['age']
    condition = request.form['condition']
    password= request.form['password']
    number = request.form['emergencyN']

    collection.insert_one({
        'name': name,
        'age': age,
        'condition': condition,
        'password' : password,
        'number' : number
    })

    # adding on onem2m server
    # OM2M Config
    OM2M_BASE = "http://localhost:5089/~/in-cse/in-name/PATIENT_DATA"
    OM2M_HEADERS_CNT = {
        "X-M2M-Origin": "admin:admin",              # originator
        "X-M2M-RI": "req-" + name,                  # request ID
        "Content-Type": "application/json;ty=3"     # ty=3 for container
    }

    # Payload to create a container for this patient
    om2m_payload = {
        "m2m:cnt": {
            "rn": name  # resource name = patient name
        }
    }

    # Send to OM2M
    om2m_res = requests.post(
        OM2M_BASE,
        headers=OM2M_HEADERS_CNT,
        data=json.dumps(om2m_payload)
    )

    # Optional: Check response
    print("OM2M Response:", om2m_res.status_code, om2m_res.text)
    if om2m_res.status_code in [201, 409]:
        container_names = ["sensor1", "sensor2"]

        for i in container_names:
            OM2M_HEADERS_CNT["X-M2M-RI"] = f"req-{name}-{i}"
            
            # Create container payload
            container_payload = {
                "m2m:cnt": {
                    "rn": i
                }
            }
            
            # Send container creation request
            container_url = f"{OM2M_BASE}/{name}"
            container_response = requests.post(
                container_url,
                headers=OM2M_HEADERS_CNT,
                data=json.dumps(container_payload)
            )
            print(f"{i} container creation response: {container_response.status_code}")

    return redirect(url_for('admin_dashboard'))

@app.route('/delete_patient/<patient_id>', methods=['GET'])
def delete_patient(patient_id):
    data= collection.find_one({'_id': ObjectId(patient_id)})
    name=data["name"]
    collection.delete_one({'_id': ObjectId(patient_id)})
    url = f"http://localhost:5089/~/in-cse/in-name/PATIENT_DATA/{name}"
    header ={
        "X-M2M-Origin": "admin:admin",  
        "X-M2M-RI": f"del{name}"
    }
    res = requests.delete(url, headers=header)
    print("Delete Response:", res.status_code, res.text)
    return redirect(url_for('admin_dashboard'))

@app.route('/emergency', methods=['GET'])
def send_emergency_sms():
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body="🚨 EMERGENCY! Patient needs immediate attention!",
            from_=TWILIO_PHONE_NUMBER,
            to=EMERGENCY_CONTACT
        )
        return jsonify({"message": "Emergency alert sent successfully!", "sid": message.sid})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
