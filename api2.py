from flask import Flask, request, jsonify
from flask_cors import CORS
# MODIFIED: Make sure the import name matches your file name
import VandiGO_Kannamma_integrated1 as Vandigo_Kannamma

app = Flask(__name__)
CORS(app)

# --- In-Memory Storage for Ride State ---
# In a real application, this would be a database (like Redis or a SQL DB)
pending_rides = {} # Key: driver_user_id, Value: ride_details
accepted_rides = {} # Key: ride_id, Value: ride_details

# Endpoint to evaluate price (remains mostly the same)
@app.route('/evaluate-price', methods=['POST'])
def evaluate_price():
    data = request.get_json()
    # This endpoint can be simplified to only return price and time if needed
    # For now, we'll use the full coordinator for simplicity
    try:
        ride_details = Vandigo_Kannamma.main_coordinator(
            data.get('pickup'), data.get('drop'), data.get('vehicle_type').capitalize()
        )
        # Only return what's needed for the quote
        return jsonify({
            "price": ride_details["price"],
            "arrival_time": ride_details["driver_to_customer"]["time_minutes"],
            "trip_time": ride_details["customer_to_destination"]["time_minutes"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# MODIFIED: New endpoint for a user to request a ride
@app.route('/request-ride', methods=['POST'])
def request_ride():
    data = request.get_json()
    try:
        # Find a driver and get all ride details
        ride_details = Vandigo_Kannamma.main_coordinator(
            data.get('pickup'), data.get('drop'), data.get('vehicle_type').capitalize()
        )
        driver_id = ride_details['driver_user_id']
        
        # Store the ride request for the driver to see
        pending_rides[driver_id] = ride_details
        
        return jsonify({"ride_id": ride_details['ride_id'], "status": "pending"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# MODIFIED: New endpoint for the driver to check for pending trips
@app.route('/get-pending-trips/<driver_id>', methods=['GET'])
def get_pending_trips(driver_id):
    if driver_id in pending_rides:
        return jsonify({"trip": pending_rides[driver_id]})
    return jsonify({"trip": None})

# MODIFIED: New endpoint for the driver to accept a ride
@app.route('/accept-ride', methods=['POST'])
def accept_ride():
    data = request.get_json()
    driver_id = data.get('driver_id')
    ride_id = data.get('ride_id')
    
    if driver_id in pending_rides and pending_rides[driver_id]['ride_id'] == ride_id:
        ride_details = pending_rides.pop(driver_id) # Remove from pending
        accepted_rides[ride_id] = ride_details    # Add to accepted
        return jsonify({"status": "success", "message": "Ride accepted"})
    return jsonify({"status": "error", "message": "Ride not found or already taken"}), 404

# MODIFIED: New endpoint for the user to check the status of their ride request
@app.route('/check-ride-status/<ride_id>', methods=['GET'])
def check_ride_status(ride_id):
    if ride_id in accepted_rides:
        return jsonify({"status": "accepted", "ride_details": accepted_rides[ride_id]})
    # Optional: Add a timeout logic here
    return jsonify({"status": "pending"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)