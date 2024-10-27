import requests
import openai
import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load environment variables from .env file
load_dotenv()

# API Keys
EIA_API_KEY = os.getenv("EIA_API_KEY")
CARBON_INTERFACE_API_KEY = os.getenv("CARBON_INTERFACE_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

def get_energy_data():
    try:
        eia_url = f"https://api.eia.gov/v2/petroleum/pri/gnd/data/?frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={EIA_API_KEY}"
        response = requests.get(eia_url)
        if response.status_code == 200:
            data = response.json()
            latest_data = data['response']['data'][0]
            return {
                "price_per_gallon": latest_data['value'],
                "period": latest_data['period']
            }
        else:
            print(f"Failed to get petroleum price data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in get_energy_data: {str(e)}")
        return None

def calculate_emissions(distance_km):
    try:
        url = "https://www.carboninterface.com/api/v1/estimates"
        headers = {
            "Authorization": f"Bearer {CARBON_INTERFACE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "type": "vehicle",
            "distance_unit": "km",
            "distance_value": distance_km,
            "vehicle_model_id": "7268a9b7-17e8-4c8d-acca-57059252afe9"
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            emissions_data = response.json()
            return {
                "carbon_g": emissions_data['data']['attributes']['carbon_g'],
                "carbon_kg": emissions_data['data']['attributes']['carbon_g'] / 1000
            }
        else:
            print(f"Failed to calculate carbon emissions: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Error in calculate_emissions: {str(e)}")
        return None

def get_weather_data(location):
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(weather_url)
        if response.status_code == 200:
            weather_data = response.json()
            return {
                "temperature": weather_data['main']['temp'],
                "weather": weather_data['weather'][0]['description'],
                "wind_speed": weather_data['wind']['speed']
            }
        else:
            print(f"Failed to get weather data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in get_weather_data: {str(e)}")
        return None

def get_eco_route(origin_coords, destination_coords):
    try:
        # Ensure coordinates are in the correct format and order for OpenRouteService
        formatted_origin = [origin_coords[1], origin_coords[0]]
        formatted_destination = [destination_coords[1], destination_coords[0]]
        
        headers = {
            "Authorization": OPENROUTESERVICE_API_KEY,  # Remove 'Bearer' prefix
            "Content-Type": "application/json"
        }
        
        # Debug logging
        print(f"Sending coordinates to ORS: {formatted_origin}, {formatted_destination}")
        
        payload = {
            "coordinates": [formatted_origin, formatted_destination],
            "profile": "driving-car"
        }
        
        # Use the geojson endpoint as in the original code
        ors_url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
        response = requests.post(ors_url, headers=headers, json=payload)
        
        print(f"ORS Response Status: {response.status_code}")
        if response.status_code != 200:
            print(f"ORS Error Response: {response.text}")
            return None
            
        route_data = response.json()
        
        if "features" in route_data and len(route_data["features"]) > 0:
            route_feature = route_data["features"][0]
            coordinates = route_feature["geometry"]["coordinates"]
            properties = route_feature["properties"]
            
            # Convert coordinates back to [latitude, longitude] for frontend
            converted_coordinates = [[coord[1], coord[0]] for coord in coordinates]
            
            # Extract duration in minutes and distance in km
            duration_minutes = round(properties["segments"][0]["duration"] / 60)
            distance_km = properties["segments"][0]["distance"] / 1000
            
            # Extract turn-by-turn directions from steps
            directions = []
            for segment in properties["segments"]:
                for step in segment.get("steps", []):
                    if "instruction" in step:
                        directions.append(step["instruction"])
            
            return {
                "distance_km": distance_km,
                "duration_minutes": duration_minutes,
                "coordinates": converted_coordinates,
                "directions": directions
            }
        else:
            print("No routes found in the response.")
            print("Full response:", route_data)
            return None
            
    except Exception as e:
        print(f"Error in get_eco_route: {str(e)}")
        return None

def simulate_optimized_route(route_data, vehicle):
    # Simulate optimized route with improvements
    return {
        "optimized_distance_km": route_data["distance_km"],  # Assume same distance
        "optimized_duration_minutes": round(route_data["duration_minutes"] * 0.95),  # 5% faster
        "optimized_carbon_emissions": {
            "carbon_kg": route_data["emissions"]["carbon_kg"] * 0.9  # 10% reduction
        }
    }

def generate_openai_prompt(route_data, energy_data, carbon_emissions, weather_origin, weather_destination, vehicle):
    prompt = (
        f"Based on the following information:\n"
        f"- Distance: {route_data['distance_km']} km\n"
        f"- Estimated Time: {route_data['duration_minutes']} minutes\n"
        f"- Energy Price: ${energy_data['price_per_gallon']} per gallon\n"
        f"- Estimated Carbon Emissions: {carbon_emissions['carbon_kg']:.2f} kg of CO₂\n"
        f"- Weather at Origin: {weather_origin['weather']}, Temperature: {weather_origin['temperature']}°C, Wind Speed: {weather_origin['wind_speed']} m/s\n"
        f"- Weather at Destination: {weather_destination['weather']}, Temperature: {weather_destination['temperature']}°C, Wind Speed: {weather_destination['wind_speed']} m/s\n"
        f"- Vehicle Type: {vehicle['type']}, Fuel Efficiency: {vehicle['efficiency']} km/l, Fuel Type: {vehicle['fuel_type']}\n"
        f"Provide a recommendation for reducing emissions and optimizing energy consumption for this route."
    )
    return prompt

def get_openai_recommendation(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant that provides route and energy optimization advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            n=1,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Failed to generate recommendation."

@app.route('/get_route_recommendation', methods=['POST'])
def get_route_recommendation():
    try:
        data = request.json
        origin_coords = data['origin_coords']
        destination_coords = data['destination_coords']
        vehicle = data['vehicle']

        print("Received coordinates:", origin_coords, destination_coords)

        # Get route data with directions
        route_data = get_eco_route(origin_coords, destination_coords)
        
        if route_data is None:
            return jsonify({
                "error": "Unable to calculate route with provided coordinates"
            }), 400

        # Get energy data
        energy_data = get_energy_data() or {
            "price_per_gallon": 3.50,  # Fallback value
            "period": "latest"
        }
        
        # Get weather data
        weather_origin = get_weather_data("San Francisco") or {
            "temperature": 20,
            "weather": "clear",
            "wind_speed": 5
        }
        
        weather_destination = get_weather_data("Los Angeles") or {
            "temperature": 25,
            "weather": "clear",
            "wind_speed": 5
        }

        # Calculate emissions
        carbon_emissions = calculate_emissions(route_data["distance_km"])
        if carbon_emissions is None:
            carbon_emissions = {
                "carbon_g": route_data["distance_km"] * 2310,  # Fallback calculation
                "carbon_kg": route_data["distance_km"] * 2.31
            }

        # Generate optimized route data
        optimized_route = simulate_optimized_route({
            "distance_km": route_data["distance_km"],
            "duration_minutes": route_data["duration_minutes"],
            "emissions": carbon_emissions
        }, vehicle)

        # Get AI recommendation
        prompt = generate_openai_prompt(route_data, energy_data, carbon_emissions, 
                                     weather_origin, weather_destination, vehicle)
        recommendation = get_openai_recommendation(prompt)

        # Create comparison output
        comparison = {
            "original": {
                "distance_km": route_data["distance_km"],
                "duration_minutes": route_data["duration_minutes"],
                "carbon_emissions_kg": carbon_emissions["carbon_kg"]
            },
            "optimized": {
                "distance_km": optimized_route["optimized_distance_km"],
                "duration_minutes": optimized_route["optimized_duration_minutes"],
                "carbon_emissions_kg": optimized_route["optimized_carbon_emissions"]["carbon_kg"]
            }
        }

        return jsonify({
            "route": route_data["coordinates"],
            "directions": route_data["directions"],
            "comparison": comparison,
            "recommendation": recommendation
        })

    except Exception as e:
        print(f"Error in route recommendation: {str(e)}")
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == "__main__":
    # Check if required API keys are present
    missing_keys = []
    for key_name, key_value in {
        "EIA_API_KEY": EIA_API_KEY,
        "CARBON_INTERFACE_API_KEY": CARBON_INTERFACE_API_KEY,
        "WEATHER_API_KEY": WEATHER_API_KEY,
        "OPENROUTESERVICE_API_KEY": OPENROUTESERVICE_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY
    }.items():
        if not key_value:
            missing_keys.append(key_name)
    
    if missing_keys:
        print(f"Warning: The following API keys are missing: {', '.join(missing_keys)}")
        print("Some features may not work properly.")
    
    app.run(host="0.0.0.0", port=5050)
