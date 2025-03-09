import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend to prevent threading issues

from flask import Flask, render_template, send_file, make_response, request, redirect, url_for
import matplotlib.pyplot as plt
import numpy as np
import os

app = Flask(__name__)

# Ensure the 'static' directory exists
if not os.path.exists("static"):
    os.makedirs("static")

# Store last 15 values (initial values)
spo2_values = list(95 + np.random.normal(0, 1, 15))  # Blood Oxygen Levels
pulse_values = list(75 + np.random.normal(0, 2, 15))  # Pulse Rate
temp_values = list(37 + np.random.normal(0, 0.5, 15))  # Body Temperature


def update_data():
    """ Updates the last 15 values by adding a new random value at the end 
        and removing the first value. """
    global spo2_values, pulse_values, temp_values
    
    # Append new random value & remove the oldest one
    spo2_values.append(95 + np.random.normal(0, 1))
    spo2_values.pop(0)

    pulse_values.append(75 + np.random.normal(0, 2))
    pulse_values.pop(0)

    temp_values.append(37 + np.random.normal(0, 0.5))
    temp_values.pop(0)


def generate_graphs():
    """ Generates the graphs using the rolling 15 data points. """
    update_data()  # Update data before plotting
    t = np.arange(-30, 0, 2)[-15:]  # Keep only last 15 timestamps

    fig, axs = plt.subplots(3, 1, figsize=(6, 10))

    # Blood Oxygen Graph
    axs[0].plot(t, spo2_values, color='blue', marker='o', label="SpO2 Level")
    axs[0].set_title("Blood Oxygen Levels (SpO2)")
    axs[0].set_ylabel("%")
    axs[0].set_xlabel("sec")
    axs[0].legend()
    axs[0].grid()

    # Pulse Rate Graph
    axs[1].plot(t, pulse_values, color='red', marker='o', label="Pulse Rate")
    axs[1].set_title("Pulse Rate")
    axs[1].set_ylabel("BPM")
    axs[1].set_xlabel("sec")
    axs[1].legend()
    axs[1].grid()

    # Body Temperature Graph
    axs[2].plot(t, temp_values, color='green', marker='o', label="Body Temperature")
    axs[2].set_title("Body Temperature")
    axs[2].set_ylabel("°C")
    axs[2].set_xlabel("sec")
    axs[2].legend()
    axs[2].grid()

    plt.tight_layout()
    plt.savefig("static/graph.png")
    plt.close()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/submit', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    if username == 'admin' and password == '12345':
        return redirect(url_for('patient'))  # Redirect to index.html after login
    else:
        return redirect(url_for('home', error="Invalid credentials"))  # Pass error message

@app.route('/patient')
def patient():
    return render_template('index.html')  # Make sure this file exists

@app.route('/graph')
def get_graph():
    generate_graphs()  # Generate new graphs before sending
    response = make_response(send_file("static/graph.png", mimetype='image/png'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    app.run(debug=True)
