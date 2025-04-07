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

app = Flask(__name__)

# Ensure the 'static' directory exists
if not os.path.exists("static"):
    os.makedirs("static")

# Connect to MongoDB
client = MongoClient() # add your connection string
db = client["iot_project"]
collection = db["patients"]

# Store last 15 values (initial values)
spo2_values = [0] * 15
pulse_values = [0] * 15
temp_values = [0] * 15

TWILIO_ACCOUNT_SID = "AC4f8a9ad45e50f74d460eb475777dc4cb"
TWILIO_AUTH_TOKEN = ""  # Replace with your actual auth token
TWILIO_PHONE_NUMBER = "+16073676189"  # Your Twilio number
EMERGENCY_CONTACT = "+919392733940"  # Number to send SMS



#fetching latest data from om2m server
def update_data(patient):
    url = f"http://localhost:5089/~/in-cse/in-name/PATIENT_DATA/{patient}/la"
    headers = {
        "X-M2M-Origin": "admin:admin",
        "Accept": "application/json"
    }
    global spo2_values, pulse_values, temp_values
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            content = data["m2m:cin"]["con"]
            values = content.split(",")
            return float(values[0]), float(values[1]), float(values[2])  # SpO2, pulse, temp
        else:
            print("Failed to fetch from OM2M:", res.status_code)
            return None
    except Exception as e:
        print("Error:", e)
        return None



def generate_graphs(patient):
    new_data=update_data(patient)

    #updating the values    
    if new_data:
        spo2, pulse, temp = new_data
        spo2_values.append(spo2)
        spo2_values.pop(0)
        pulse_values.append(pulse)
        pulse_values.pop(0)
        temp_values.append(temp)
        temp_values.pop(0)

    t = np.arange(-30, 0, 2)[-15:]
    fig, axs = plt.subplots(3, 1, figsize=(6, 10))

    axs[0].plot(t, spo2_values, color='blue', marker='o', label="SpO2 Level")
    axs[0].set_title("Blood Oxygen Levels (SpO2)")
    axs[0].set_ylabel("%")
    axs[0].legend()
    axs[0].grid()

    axs[1].plot(t, pulse_values, color='red', marker='o', label="Pulse Rate")
    axs[1].set_title("Pulse Rate")
    axs[1].set_ylabel("BPM")
    axs[1].legend()
    axs[1].grid()

    axs[2].plot(t, temp_values, color='green', marker='o', label="Body Temperature")
    axs[2].set_title("Body Temperature")
    axs[2].set_ylabel("°C")
    axs[2].legend()
    axs[2].grid()

    plt.tight_layout()
    plt.savefig("static/graph.png")
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

    global spo2_values,pulse_values,temp_values 
    spo2_values = [0] * 15
    pulse_values = [0] * 15
    temp_values = [0] * 15
    
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

    collection.insert_one({
        'name': name,
        'age': age,
        'condition': condition,
        'password' : password
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
