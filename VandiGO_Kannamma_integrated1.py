import joblib
import requests
import polyline
import numpy as np
from urllib.parse import urlencode
from math import radians, sin, cos, sqrt, atan2
import uuid # Used to generate unique ride IDs

# --- Constants ---
GOOGLE_API_KEY = "AIzaSyCeLjhCEHBzwDXHR7ZhOY1r0-OcQvt3waI" # Replace with your key
OPENWEATHER_API_KEY = "0b1a30cc3f3aa533efea3f6b3b851746" # Replace with your key
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyC6KqinXb8FhqcI6uwEfl4h0EIvAkFNqfTrGxVkTPdnDpJxVFqmbFDdw4qxhv9oc5w/exec" # Replace with your new URL

# --- Machine Learning Model Loading ---
model = joblib.load("rain_traffic_model.pkl")

def get_driver_details(vehicle_no):
    """Fetches driver details from the Google Sheet using vehicle number."""
    try:
        params = {"action": "getDriverDetails", "vehicle_no": vehicle_no}
        response = requests.get(WEB_APP_URL, params=params).json()
        
        if response.get("status") == "success" and "driver" in response:
            driver = response["driver"]
            return driver.get("name", "N/A"), driver.get("phone", "N/A")
        else:
            return "N/A", "N/A"
    except requests.exceptions.RequestException as e:
        print(f"Error fetching driver details: {e}")
        return "N/A", "N/A"

def get_lat_lon(location):
    """Converts a location address to latitude and longitude."""
    params = {"address": location, "key": GOOGLE_API_KEY}
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{urlencode(params)}"
    response = requests.get(url).json()
    if response["status"] == "OK":
        lat = response["results"][0]["geometry"]["location"]["lat"]
        lon = response["results"][0]["geometry"]["location"]["lng"]
        return lat, lon
    else:
        raise Exception(f"Geocoding API Error: {response['status']}")

def filter_drivers_by_radius(origin_lat, origin_lon, driver_locations):
    """Filters drivers within expanding radii from the origin."""
    def calculate_distance(lat1, lon1, lat2, lon2):
        R = 6371
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    radii_km = [5, 10, 15, 20, 25, 50]
    for radius in radii_km:
        filtered_locations = [
            loc for loc in driver_locations
            if calculate_distance(origin_lat, origin_lon, loc["coords"][0], loc["coords"][1]) <= radius
        ]
        if filtered_locations:
            return filtered_locations
    return []

def best_route_time(origin_lat, origin_lon, dest_lat, dest_lon, waypoint_step=30):
    """Calculates the best route time, adjusted for weather-predicted traffic."""
    def get_rain(lat, lon):
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url).json()
        return response.get("rain", {}).get("1h", 0.0) if response.get("cod") == 200 else 0.0

    url = (
        f"https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin_lat},{origin_lon}&destination={dest_lat},{dest_lon}"
        f"&alternatives=true&mode=driving&departure_time=now&key={GOOGLE_API_KEY}"
    )
    response = requests.get(url).json()
    if response["status"] != "OK":
        raise Exception(f"Google Maps API Error: {response['status']}")

    best_time = float('inf')
    for route in response["routes"]:
        leg = route["legs"][0]
        base_time = leg.get("duration_in_traffic", {}).get("value", leg["duration"]["value"])
        coords = polyline.decode(route["overview_polyline"]["points"])
        sampled_points = coords[::waypoint_step] or coords
        
        rain_values = [get_rain(lat, lon) for lat, lon in sampled_points]
        avg_rain = sum(rain_values) / len(rain_values) if rain_values else 0.0
        
        predicted_traffic = model.predict([[avg_rain]])[0]
        min_traffic = 1e-6 + np.min(model.predict([[0]]))
        factor = predicted_traffic / min_traffic
        adjusted_time = int(base_time * factor)
        
        if adjusted_time < best_time:
            best_time = adjusted_time
            
    return best_time // 60 if best_time != float('inf') else -1

def best_route_distance(origin_lat, origin_lon, dest_lat, dest_lon):
    """Finds the shortest distance route and its coordinates."""
    url = (
        f"https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin_lat},{origin_lon}&destination={dest_lat},{dest_lon}"
        f"&alternatives=true&mode=driving&key={GOOGLE_API_KEY}"
    )
    response = requests.get(url).json()
    if response["status"] != "OK":
        raise Exception(f"Google Maps API Error: {response['status']}")

    best_distance = float('inf')
    best_coords = None
    for route in response["routes"]:
        distance = route["legs"][0]["distance"]["value"]
        if distance < best_distance:
            best_distance = distance
            best_coords = polyline.decode(route["overview_polyline"]["points"])
            
    return {"distance_meters": best_distance, "route_coords": best_coords}


def find_best_driver(origin_location, vehicle_type):
    """Finds the closest available driver and returns their details."""
    try:
        response = requests.get(WEB_APP_URL, params={"action": "getLocations"}).json()
        if response.get("status") != "success":
            raise Exception("Failed to fetch driver locations from Google Sheet.")
        
        locations_data = response.get("locations", [])
        
        
        driver_locations = [
            {
                "vehicle_no": d["vehicle_no"],
                "coords": (float(d["latitude"]), float(d["longitude"])),
                "user_id": d["user_id"] # <-- Changed "User id" to "user_id"
            }
            for d in locations_data if d["vehicle_type"] == vehicle_type # <-- Changed "Vehicle type" to "vehicle_type"
        ]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching data from web app: {e}")

    origin_coords = get_lat_lon(origin_location)
    
    shortlisted_drivers = filter_drivers_by_radius(origin_coords[0], origin_coords[1], driver_locations)
    if not shortlisted_drivers:
        raise Exception("No drivers found nearby.")

    best_driver = None
    min_time = float('inf')
    for driver in shortlisted_drivers:
        time = best_route_time(origin_coords[0], origin_coords[1], driver["coords"][0], driver["coords"][1])
        if time < min_time:
            min_time = time
            best_driver = driver
    
    if not best_driver:
        raise Exception("Could not determine the best driver from the shortlist.")

    return best_driver["user_id"], best_driver["vehicle_no"], best_driver["coords"]

# MODIFIED: main_coordinator now also returns the driver_user_id
def main_coordinator(origin_location, destination_location, vehicle_type):
    """Main function to coordinate all steps and return ride details."""
    driver_user_id, best_driver_no, best_driver_coords = find_best_driver(origin_location, vehicle_type)
    driver_name, driver_phone = get_driver_details(best_driver_no)

    origin_coords = get_lat_lon(origin_location)
    destination_coords = get_lat_lon(destination_location)
  
    # Create a unique ID for this ride request
    ride_id = str(uuid.uuid4())

    d2c_route = best_route_distance(best_driver_coords[0], best_driver_coords[1], origin_coords[0], origin_coords[1])
    d2c_time = best_route_time(best_driver_coords[0], best_driver_coords[1], origin_coords[0], origin_coords[1])
    
    c2d_route = best_route_distance(origin_coords[0], origin_coords[1], destination_coords[0], destination_coords[1])
    c2d_time = best_route_time(origin_coords[0], origin_coords[1], destination_coords[0], destination_coords[1])

    # Pricing
    price = 0
    if vehicle_type == "Jumbo":
      price = c2d_route["distance_meters"] * 0.06
    elif vehicle_type == "Regular":
      price = c2d_route["distance_meters"] * 0.045

    # Consolidate all ride information into a single dictionary
    ride_details = {
        "ride_id": ride_id,
        "driver_user_id": driver_user_id,
        "driver_vehicle_no": best_driver_no,
        "driver_name": driver_name,
        "driver_phone": driver_phone,
        "pickup_location": origin_location,
        "drop_location": destination_location,
        "driver_to_customer": {
            "route_coords": d2c_route["route_coords"],
            "time_minutes": d2c_time
        },
        "customer_to_destination": {
            "route_coords": c2d_route["route_coords"],
            "time_minutes": c2d_time
        },
        "price": round(price, 2)
    }

    return ride_details
