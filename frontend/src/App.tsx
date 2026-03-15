import { useEffect, useState } from "react";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch(() => setMessage("Backend not connected"));
  }, []);

  return (
    <div style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>Perception AI</h1>
      <p>Status: {message || "Loading..."}</p>
    </div>
  );
}

export default App;
