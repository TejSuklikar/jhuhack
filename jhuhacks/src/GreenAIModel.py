import requests
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# API Keys
GOOGLE_MAPS_API_KEY = "AIzaSyDDScCaR3ATCumlK52NNGmy07F8eQxqERI"
EIA_API_KEY = "EVJa2KTyMBxNAve9Hn6e8ubqAidOTw3vM1wQOzhA"
CARBON_INTERFACE_API_KEY = "97rxAZ4XpWJH10sQcgVORQ"
WEATHER_API_KEY = "251c2d97f4f93e7042fc5eb2c217c2b9"
OPENROUTESERVICE_API_KEY = "5b3ce3597851110001cf62487fc31e9875df47f5bdff20facf1b8cce"
OPENAI_API_KEY = "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"

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Function to get traffic and distance data from Google Maps API
def get_traffic_data(origin, destination):
    google_maps_url = (
        f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={GOOGLE_MAPS_API_KEY}"
    )
    response = requests.get(google_maps_url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            traffic_info = data['routes'][0]['legs'][0]
            distance = traffic_info['distance']['value'] / 1000  # Convert meters to kilometers
            duration = traffic_info['duration_in_traffic']['value'] / 60  # Convert seconds to minutes
            return {
                "distance_km": distance,
                "duration_minutes": duration,
                "traffic": traffic_info['duration_in_traffic']['text']
            }
        else:
            print(f"Error with Google Maps API: {data['status']}")
    else:
        print(f"Failed to get traffic data: {response.status_code}")
    return None

# Function to get energy price data from EIA API
def get_energy_data():
    eia_url = f"https://api.eia.gov/series/?api_key={EIA_API_KEY}&series_id=ELEC.PRICE.US-ALL.M"
    response = requests.get(eia_url)
    if response.status_code == 200:
        data = response.json()
        latest_data = data['series'][0]['data'][0]  # Get the latest data point
        energy_price = latest_data[1]  # The second value is the price
        return {
            "price_per_kWh": energy_price
        }
    else:
        print(f"Failed to get energy data: {response.status_code}")
    return None

# Function to calculate carbon emissions using Carbon Interface API
def calculate_emissions(distance_km, vehicle_model="passenger_vehicle"):
    url = "https://www.carboninterface.com/api/v1/estimates"
    headers = {
        "Authorization": f"Bearer {CARBON_INTERFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "type": "vehicle",
        "distance_unit": "km",
        "distance_value": distance_km,
        "vehicle_model_id": vehicle_model  # Vehicle model ID can be customized
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        emissions_data = response.json()
        return emissions_data['data']['attributes']['carbon_kg']  # Carbon emissions in kg
    else:
        print(f"Failed to calculate carbon emissions: {response.status_code}")
    return None

# Function to get weather data from OpenWeatherMap API
def get_weather_data(location):
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(weather_url)
    if response.status_code == 200:
        weather_data = response.json()
        return {
            "temperature": weather_data['main']['temp'],  # Temperature in Celsius
            "weather": weather_data['weather'][0]['description'],  # Weather condition description
            "wind_speed": weather_data['wind']['speed']  # Wind speed in m/s
        }
    else:
        print(f"Failed to get weather data: {response.status_code}")
    return None

# Function to get eco-friendly route using OpenRouteService API
def get_eco_route(origin_coords, destination_coords, vehicle_type="electric_vehicle"):
    headers = {
        "Authorization": OPENROUTESERVICE_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "coordinates": [origin_coords, destination_coords],
        "profile": "driving-car",
        "options": {
            "vehicle_type": vehicle_type  # electric_vehicle, diesel, etc.
        }
    }
    ors_url = "https://api.openrouteservice.org/v2/directions/driving-car"
    response = requests.post(ors_url, headers=headers, json=payload)
    if response.status_code == 200:
        route_data = response.json()
        return route_data
    else:
        print(f"Failed to get route from OpenRouteService API: {response.status_code}")
    return None

# Function to generate OpenAI API prompt
def generate_openai_prompt(traffic_data, energy_data, carbon_emissions, weather_origin, weather_destination, vehicle):
    prompt = (
        f"Based on the following information:\n"
        f"- Distance: {traffic_data['distance_km']} km\n"
        f"- Estimated Travel Time: {traffic_data['duration_minutes']} minutes\n"
        f"- Current Traffic: {traffic_data['traffic']}\n"
        f"- Energy Price: ${energy_data['price_per_kWh']} per kWh\n"
        f"- Estimated Carbon Emissions: {carbon_emissions} kg of CO₂\n"
        f"- Weather at Origin: {weather_origin['weather']}, Temperature: {weather_origin['temperature']}°C, Wind Speed: {weather_origin['wind_speed']} m/s\n"
        f"- Weather at Destination: {weather_destination['weather']}, Temperature: {weather_destination['temperature']}°C, Wind Speed: {weather_destination['wind_speed']} m/s\n"
        f"- Vehicle Type: {vehicle['type']}, Fuel Efficiency: {vehicle['efficiency']} km/l, Fuel Type: {vehicle['fuel_type']}\n"
        f"Provide a recommendation for reducing emissions and optimizing energy consumption for this route."
    )
    return prompt

# Function to call OpenAI API for generating recommendations
def get_openai_recommendation(prompt):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",  # GPT-4 model (or GPT-3.5)
            prompt=prompt,
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.7
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Failed to generate recommendation."

# Function to integrate all the APIs and get final recommendation
def get_route_recommendation_with_openai(origin, destination, vehicle):
    # 1. Get traffic data from Google Maps
    traffic_data = get_traffic_data(origin, destination)
    if not traffic_data:
        return "Failed to retrieve traffic data."

    # 2. Get energy price data from EIA API
    energy_data = get_energy_data()
    if not energy_data:
        return "Failed to retrieve energy data."

    # 3. Get weather data for origin and destination
    weather_origin = get_weather_data(origin)
    weather_destination = get_weather_data(destination)
    if not weather_origin or not weather_destination:
        return "Failed to retrieve weather data."

    # 4. Calculate carbon emissions using Carbon Interface API
    carbon_emissions = calculate_emissions(traffic_data["distance_km"], vehicle["model"])
    if carbon_emissions is None:
        return "Failed to calculate carbon emissions."

    # 5. Generate a prompt for OpenAI using the retrieved data
    prompt = generate_openai_prompt(traffic_data, energy_data, carbon_emissions, weather_origin, weather_destination, vehicle)

    # 6. Call OpenAI API to generate recommendation
    recommendation = get_openai_recommendation(prompt)
    return recommendation

# Example usage
if __name__ == "__main__":
    origin = "San Francisco, CA"
    destination = "Los Angeles, CA"

    # Vehicle characteristics
    vehicle = {
        "type": "Electric Vehicle",
        "model": "tesla_model_3",
        "efficiency": 6.0,  # km/kWh
        "fuel_type": "electric"
    }

    recommendation = get_route_recommendation_with_openai(origin, destination, vehicle)
    print(f"AI-Generated Recommendation: {recommendation}")
