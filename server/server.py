import matplotlib
matplotlib.use('Agg')
from pymongo import MongoClient
from flask import Flask, render_template, send_file, make_response, request, redirect, url_for, jsonify
import matplotlib.pyplot as plt
import numpy as np
import os
from bson.objectid import ObjectId
from twilio.rest import Client

app = Flask(__name__)

# Ensure the 'static' directory exists
if not os.path.exists("static"):
    os.makedirs("static")

# Connect to MongoDB
client = MongoClient("mongodb+srv://visheshsinghal613:@cluster0.2qzfd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["iot_project"]
collection = db["patients"]

# Store last 15 values (initial values)
spo2_values = list(95 + np.random.normal(0, 1, 15))
pulse_values = list(75 + np.random.normal(0, 2, 15))
temp_values = list(37 + np.random.normal(0, 0.5, 15))

TWILIO_ACCOUNT_SID = "AC4f8a9ad45e50f74d460eb475777dc4cb"
TWILIO_AUTH_TOKEN = ""  # Replace with your actual auth token
TWILIO_PHONE_NUMBER = "+16073676189"  # Your Twilio number
EMERGENCY_CONTACT = "+919392733940"  # Number to send SMS

def update_data():
    global spo2_values, pulse_values, temp_values
    spo2_values.append(95 + np.random.normal(0, 1))
    spo2_values.pop(0)
    pulse_values.append(75 + np.random.normal(0, 2))
    pulse_values.pop(0)
    temp_values.append(37 + np.random.normal(0, 0.5))
    temp_values.pop(0)

def generate_graphs():
    update_data()
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
        return redirect(url_for('patient'))
    else:
        return redirect(url_for('home', error="Invalid credentials"))

@app.route('/admin')
def admin_dashboard():
    patients = list(collection.find())
    return render_template('admin_dashboard.html', patients=patients)

@app.route('/add_patient', methods=['POST'])
def add_patient():
    name = request.form['name']
    age = request.form['age']
    condition = request.form['condition']

    collection.insert_one({
        'name': name,
        'age': age,
        'condition': condition
    })
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_patient/<patient_id>', methods=['GET'])
def delete_patient(patient_id):
    collection.delete_one({'_id': ObjectId(patient_id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/patient')
def patient():
    return render_template('index.html')

@app.route('/graph')
def get_graph():
    generate_graphs()
    response = make_response(send_file("static/graph.png", mimetype='image/png'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

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
