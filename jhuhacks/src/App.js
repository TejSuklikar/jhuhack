import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

function App() {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [route, setRoute] = useState(null);
  const [emissionsSaved, setEmissionsSaved] = useState(0);
  const [loading, setLoading] = useState(false);
  const [routeDistance, setRouteDistance] = useState(0);
  const [routeTime, setRouteTime] = useState(0);
  const [userLocation, setUserLocation] = useState(null);
  const [center, setCenter] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [recommendation, setRecommendation] = useState('');

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const userCoords = [position.coords.latitude, position.coords.longitude];
          setUserLocation(userCoords);
          setCenter(userCoords);
          
          // Reverse geocode to get address
          reverseGeocode(userCoords[0], userCoords[1])
            .then(address => {
              console.log("Reverse geocoded address:", address);
              setOrigin(address);
            })
            .catch(error => console.error('Error getting address:', error));
        },
        (error) => {
          console.error('Error fetching location', error);
          setCenter([38.8977, -77.0365]); // Default to Washington DC
        }
      );
    }
  }, []);

  // Function to convert coordinates to address (reverse geocoding)
  const reverseGeocode = async (lat, lon) => {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1`,
        { 
          headers: { 
            'Accept-Language': 'en-US,en',
            'User-Agent': 'GreenRouteSolutions/1.0'
          }
        }
      );
      const data = await response.json();
      console.log("Reverse geocoding response:", data);
      return data.display_name;
    } catch (error) {
      console.error('Reverse geocoding error:', error);
      return '';
    }
  };

  // Function to convert address to coordinates (forward geocoding)
  const geocode = async (address) => {
    try {
      const encodedAddress = encodeURIComponent(address);
      console.log("Geocoding address:", address);
      
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodedAddress}&limit=1`,
        { 
          headers: { 
            'Accept-Language': 'en-US,en',
            'User-Agent': 'GreenRouteSolutions/1.0'
          }
        }
      );
      const data = await response.json();
      console.log("Geocoding response:", data);
      
      if (data.length > 0) {
        return [parseFloat(data[0].lat), parseFloat(data[0].lon)];
      }
      throw new Error('Address not found');
    } catch (error) {
      console.error('Geocoding error:', error);
      throw error;
    }
  };

  const validateAddress = (address) => {
    if (!address) return false;
    
    // Check for minimum length
    if (address.length < 5) return false;
    
    // Check for basic address components
    const hasLetters = /[a-zA-Z]/.test(address);
    const hasNumbers = /\d/.test(address);
    const hasComma = address.includes(',');
    
    // For US addresses, check for state or zip code
    const hasStateOrZip = /([A-Z]{2}|[0-9]{5})/.test(address);
    
    // At least need letters and one of: numbers, comma, or state/zip
    const isValid = hasLetters && (hasNumbers || hasComma || hasStateOrZip);
    console.log(`Address validation for "${address}":`, isValid);
    return isValid;
  };

  const fetchRoute = async () => {
    setLoading(true);
    setErrorMessage('');
    console.log("Fetching route for:", origin, "to", destination);
    
    // Validate addresses before proceeding
    if (!validateAddress(origin)) {
      setErrorMessage('Please enter a complete origin address (e.g., "1600 Pennsylvania Ave, Washington, DC 20500")');
      setLoading(false);
      return;
    }
    
    if (!validateAddress(destination)) {
      setErrorMessage('Please enter a complete destination address (e.g., "123 Main St, San Francisco, CA 94105")');
      setLoading(false);
      return;
    }

    try {
      // Convert addresses to coordinates
      let originCoords, destinationCoords;
      
      try {
        originCoords = await geocode(origin);
        console.log("Origin coordinates:", originCoords);
      } catch (error) {
        setErrorMessage('Unable to find the origin address. Please check the spelling and try again.');
        setLoading(false);
        return;
      }
      
      try {
        destinationCoords = await geocode(destination);
        console.log("Destination coordinates:", destinationCoords);
      } catch (error) {
        setErrorMessage('Unable to find the destination address. Please check the spelling and try again.');
        setLoading(false);
        return;
      }

      const response = await fetch('http://localhost:5050/get_route_recommendation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin_coords: originCoords,
          destination_coords: destinationCoords,
          vehicle: {
            type: "gasoline_vehicle",
            model: "toyota_corolla",
            efficiency: 15.0,
            fuel_type: "gasoline"
          }
        })
      });

      const data = await response.json();
      console.log("Route API response:", data);

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch route data');
      }

      setRoute(data.route);
      setEmissionsSaved(data.emissions);
      setRouteDistance(data.distance_km);
      setRouteTime(data.duration_minutes);
      setRecommendation(data.recommendation);
      setErrorMessage('');
    } catch (error) {
      console.error('Error:', error);
      setErrorMessage(
        error.message === 'Address not found' 
          ? 'Unable to find one or both addresses. Please provide complete addresses including city and state.'
          : 'Unable to compute route. Please ensure the addresses are valid and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (minutes) => {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = Math.round(minutes % 60);
    if (hours > 0) {
      return `${hours} hr ${remainingMinutes} min`;
    }
    return `${remainingMinutes} min`;
  };

  return (
    <div className="App">
      <div className="header">
        <h1>GreenRoute Solutions</h1>
        <div className="subtitle">Optimizing routes for a sustainable future</div>
      </div>

      <div className="transparent-box input-form">
        <div className="input-group">
          <label>Origin</label>
          <input
            type="text"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            placeholder="Enter full address (e.g., 1600 Pennsylvania Ave, Washington, DC 20500)"
            disabled={loading}
          />
        </div>
        <div className="input-group">
          <label>Destination</label>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="Enter full address (e.g., 123 Main St, San Francisco, CA 94105)"
            disabled={loading}
          />
        </div>
        <button 
          onClick={fetchRoute} 
          disabled={loading || !origin || !destination} 
          className={(!loading && origin && destination) ? 'active' : ''}
        >
          {loading ? 'Optimizing...' : 'Optimize Route'}
        </button>
      </div>

      {errorMessage && <div className="error-message">{errorMessage}</div>}

      <div className="map-container">
        {center && (
          <MapContainer center={center} zoom={13} style={{ height: '500px', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors"
            />
            {userLocation && (
              <CircleMarker
                center={userLocation}
                radius={8}
                fillColor="#00008B"
                color="#00008B"
                weight={2}
                opacity={0.8}
                fillOpacity={0.9}
              />
            )}
            {route && (
              <>
                <Marker position={route[0]} />
                <Marker position={route[route.length - 1]} />
                <Polyline positions={route} color="#00008B" weight={3} />
              </>
            )}
          </MapContainer>
        )}
      </div>

      {emissionsSaved !== 0 && (
        <div className="stats-container">
          <div className="transparent-box emissions-counter">
            <h2>Emissions Reduced</h2>
            <div className="emissions-value">{(emissionsSaved / 1000).toFixed(2)}</div>
            <div className="emissions-unit">kg of CO₂</div>
          </div>
          <div className="transparent-box route-info">
            <h2>Route Information</h2>
            <div className="info-item">Distance Optimized: {routeDistance.toFixed(2)} km</div>
            <div className="info-item">Time Optimized: {formatTime(routeTime)}</div>
          </div>
          {recommendation && (
            <div className="transparent-box recommendation">
              <h2>AI Recommendation</h2>
              <div className="recommendation-text">{recommendation}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
