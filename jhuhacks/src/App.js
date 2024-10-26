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
  const [userLocation, setUserLocation] = useState(null);
  const [center, setCenter] = useState(null);

  // Get user location and set it as the origin
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const userCoords = [position.coords.latitude, position.coords.longitude];
          setUserLocation(userCoords);
          setCenter(userCoords);
          setOrigin(`${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`); // Set origin as latitude, longitude string
        },
        (error) => {
          console.error('Error fetching location', error);
          setCenter([37.7749, -122.4194]); // Default center if permission denied
        },
        { enableHighAccuracy: true }
      );
    } else {
      setCenter([37.7749, -122.4194]); // Default center if geolocation unavailable
    }
  }, []);

  useEffect(() => {
    const button = document.querySelector('button');
    if (origin && destination) {
      button.style.backgroundColor = '#00ff00';
      button.style.cursor = 'pointer';
    } else {
      button.style.backgroundColor = '#333';
      button.style.cursor = 'not-allowed';
    }
  }, [origin, destination]);

  const simulateLoading = async () => {
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 1500));
    setLoading(false);
  };

  const fetchRoute = async () => {
    if (!origin || !destination) return;
    await simulateLoading();

    const originCoordinates = [
      37.7749 + Math.random() * 0.02 - 0.01,
      -122.4194 + Math.random() * 0.02 - 0.01
    ];
    const destinationCoordinates = [
      37.7849 + Math.random() * 0.02 - 0.01,
      -122.4094 + Math.random() * 0.02 - 0.01
    ];
    
    const distance = (Math.random() * 2 + 1).toFixed(1);
    setRouteDistance(distance);

    const emissionsFactor = 252;
    const emissions = distance * emissionsFactor;
    
    setRoute([originCoordinates, destinationCoordinates]);
    setEmissionsSaved(emissions);
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
            placeholder="Enter origin"
            disabled={loading}
          />
        </div>
        <div className="input-group">
          <label>Destination</label>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="Enter destination"
            disabled={loading}
          />
        </div>
        <button 
          onClick={fetchRoute} 
          disabled={loading || !origin || !destination}
          className={`${loading ? 'loading' : ''} ${origin && destination ? 'active' : ''}`}
        >
          {loading ? 'Optimizing...' : 'Optimize Route'}
        </button>
      </div>

      <div className="map-container">
        {center && (
          <MapContainer center={center} zoom={13} style={{ height: '500px', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
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
                <Marker position={route[1]} />
                <Polyline positions={route} color="#00ff00" weight={3} />
              </>
            )}
          </MapContainer>
        )}
      </div>

      {emissionsSaved >= 0 && (
        <div className="stats-container">
          <div className="transparent-box emissions-counter">
            <h2>Emissions Reduced</h2>
            <label className="emissions-label">Carbon Emissions Lowered:</label>
            <div className="emissions-value">{emissionsSaved.toFixed(2)}</div>
            <div className="emissions-unit">grams of CO₂</div>
          </div>
          <div className="transparent-box route-info">
            <h2>Route Information</h2>
            <div className="route-details">
              <div>Distance Optimized: {routeDistance} km</div>
              <div>Estimated Time Saved: {(routeDistance * 3).toFixed(0)} min</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
