import React, { useState, useEffect } from "react";

// Taxi Dispatch UI with Login, Driver Dashboard, and User Booking Flow
// Tailwind CSS classes used for styling
// Added Light/Dark mode toggle, fancier background, and top toolbar with working back button

export default function App() {
  const [role, setRole] = useState(null); // 'user' or 'driver'
  const [driverTrips, setDriverTrips] = useState({ completed: [], pending: [] });
  const [selectedTrip, setSelectedTrip] = useState(null);
  const [darkMode, setDarkMode] = useState(false);

  // User booking flow state
  const [carType, setCarType] = useState("regular");
  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [assignedDriver, setAssignedDriver] = useState(null);
  const [expectedWaitTime, setExpectedWaitTime] = useState(null);
  const [price, setPrice] = useState(null);

  useEffect(() => {
    if (role === "driver") {
      setDriverTrips({
        completed: [
          { id: "c1", pickup: "MG Road", dropoff: "Airport", cost: 450 },
          { id: "c2", pickup: "Koramangala", dropoff: "Whitefield", cost: 600 },
        ],
        pending: [
          { id: "p1", pickup: "Indiranagar", dropoff: "Majestic", googleLink: "https://www.google.com/maps/dir/Indiranagar/Majestic" },
        ],
      });
    }
  }, [role]);

  function handleBookRide() {
    if (!pickup || !dropoff) return alert("Please enter pickup and dropoff");
    const distanceKm = 12;
    const rate = carType === "regular" ? 20 : 35;
    setPrice(distanceKm * rate);
    setExpectedWaitTime(8);
    setAssignedDriver({ name: "Ramesh", lat: 12.97, lng: 77.59 });
  }

  const bgClass = darkMode 
    ? 'bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 text-white' 
    : 'bg-gradient-to-r from-blue-100 via-sky-100 to-indigo-100 text-gray-900';
  const cardBgClass = darkMode ? 'bg-gray-800' : 'bg-white';
  const hoverClass = darkMode ? 'hover:bg-gray-700' : 'hover:bg-slate-100';

  // CORRECTED: This function now updates the state to go back to the login screen.
  const goBack = () => setRole(null);

  const Toolbar = () => (
    <div className={`w-full p-4 flex justify-between items-center ${darkMode ? 'bg-gray-900/70' : 'bg-white/70'} backdrop-blur-md shadow-md fixed top-0 left-0 z-50`}> 
      {role && <button onClick={goBack} className="text-xl font-bold p-2 rounded hover:bg-gray-300/50 transition">←</button>}
      <button onClick={() => setDarkMode(!darkMode)} className="px-3 py-1 border rounded">{darkMode ? '☀️ Light' : '🌙 Dark'}</button>
    </div>
  );

  if (!role) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${bgClass}`}> 
        <div className={`${cardBgClass} p-8 rounded-xl shadow-lg w-96 backdrop-blur-md relative`}> 
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-2xl font-semibold">Taxi Dispatch Login</h1>
            <button onClick={() => setDarkMode(!darkMode)} className="px-2 py-1 border rounded">{darkMode ? '☀️ Light' : '🌙 Dark'}</button>
          </div>
          <div className="space-y-3">
            <button onClick={() => setRole("user")} className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700 transition">Login as User</button>
            <button onClick={() => setRole("driver")} className="w-full px-4 py-2 bg-green-600 text-white rounded-lg shadow hover:bg-green-700 transition">Login as Driver</button>
          </div>
        </div>
      </div>
    );
  }

  if (role === "driver") {
    return (
      <div className={`min-h-screen pt-20 p-6 ${bgClass}`}> 
        <Toolbar />
        <div className="mb-4">
          <h1 className="text-3xl font-bold">Driver Dashboard</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className={`${cardBgClass} p-6 rounded-xl shadow-lg backdrop-blur-sm`}> 
            <h2 className="text-xl font-medium mb-3">Completed Trips</h2>
            {driverTrips.completed.map(trip => (
              <div key={trip.id} className={`border p-3 rounded mb-2 cursor-pointer ${hoverClass} transition`} onClick={() => setSelectedTrip(trip)}>
                <div>{trip.pickup} → {trip.dropoff}</div>
                <div className="text-sm text-slate-400">Cost: ₹{trip.cost}</div>
              </div>
            ))}
          </div>
          <div className={`${cardBgClass} p-6 rounded-xl shadow-lg backdrop-blur-sm`}> 
            <h2 className="text-xl font-medium mb-3">Pending Trips</h2>
            {driverTrips.pending.map(trip => (
              <div key={trip.id} className={`border p-3 rounded mb-2 cursor-pointer ${hoverClass} transition`} onClick={() => setSelectedTrip(trip)}>
                <div>{trip.pickup} → {trip.dropoff}</div>
                <div className="text-sm text-slate-400">Click to view directions</div>
              </div>
            ))}
          </div>
        </div>

        {selectedTrip && (
          <div className={`${cardBgClass} mt-6 p-6 rounded-xl shadow-lg backdrop-blur-sm`}> 
            <h3 className="text-lg font-medium mb-3">Trip Details</h3>
            <p><strong>Pickup:</strong> {selectedTrip.pickup}</p>
            <p><strong>Dropoff:</strong> {selectedTrip.dropoff}</p>
            {selectedTrip.cost && <p><strong>Cost:</strong> ₹{selectedTrip.cost}</p>}
            {selectedTrip.googleLink && (
              <a href={selectedTrip.googleLink} target="_blank" rel="noreferrer" className="text-blue-500 underline mt-2 block">View Directions in Google Maps</a>
            )}
          </div>
        )}
      </div>
    );
  }

  if (role === "user") {
    return (
      <div className={`min-h-screen pt-20 p-6 ${bgClass}`}> 
        <Toolbar />
        <div className="mb-4">
          <h1 className="text-3xl font-bold">Book a Ride</h1>
        </div>
        {!assignedDriver ? (
          <div className={`${cardBgClass} p-6 rounded-xl shadow-lg w-full max-w-lg mx-auto backdrop-blur-sm`}> 
            <label className="block mb-3">
              <span className="text-sm">Car Type</span>
              <select value={carType} onChange={e => setCarType(e.target.value)} className="w-full p-2 border rounded mt-1">
                <option value="regular">Regular (4 seater)</option>
                <option value="jumbo">Jumbo (7 seater)</option>
              </select>
            </label>
            <label className="block mb-3">
              <span className="text-sm">Pickup</span>
              <input value={pickup} onChange={e => setPickup(e.target.value)} placeholder="Enter pickup location" className="w-full p-2 border rounded mt-1" />
            </label>
            <label className="block mb-3">
              <span className="text-sm">Dropoff</span>
              <input value={dropoff} onChange={e => setDropoff(e.target.value)} placeholder="Enter dropoff location" className="w-full p-2 border rounded mt-1" />
            </label>
            <button onClick={handleBookRide} className="px-4 py-2 bg-green-600 text-white rounded-lg shadow hover:bg-green-700 transition">Book Ride</button>
          </div>
        ) : (
          <div className={`${cardBgClass} p-6 rounded-xl shadow-lg w-full max-w-lg mx-auto backdrop-blur-sm`}> 
            <h2 className="text-lg font-medium mb-3">Ride Confirmed</h2>
            <p><strong>Driver:</strong> {assignedDriver.name}</p>
            <p><strong>Price:</strong> ₹{price}</p>
            <p><strong>Expected Wait Time:</strong> {expectedWaitTime} minutes</p>
            <div className="h-64 border rounded mt-4 flex items-center justify-center text-slate-400 font-semibold">
              Live location of driver (Latitude: {assignedDriver.lat}, Longitude: {assignedDriver.lng})
            </div>
          </div>
        )}
      </div>
    );
  }
}
