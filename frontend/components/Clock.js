import { useState, useEffect } from 'react';

export default function Clock() {
  const [time, setTime] = useState(null); // Initialisiere mit null

  useEffect(() => {
    setTime(new Date()); // Setze die initiale Zeit auf dem Client
    const timerId = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => {
      clearInterval(timerId);
    };
  }, []);

  return (
    // Rendere die Zeit nur, wenn sie gesetzt ist (also auf dem Client)
    <div className="text-lg font-semibold">
      {time ? time.toLocaleTimeString() : '00:00:00'} 
    </div>
  );
}