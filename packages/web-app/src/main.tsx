/**
 * IRIS Web Application
 *
 * Voice-first AI companion for Star Atlas.
 * React frontend with chat and voice interfaces.
 */

import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import { Chat } from "./components/Chat";
import { checkHealth } from "./api/agent";
import "./styles/global.css";

type ConnectionStatus = "connected" | "connecting" | "disconnected";

function App() {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");

  useEffect(() => {
    const checkConnection = async () => {
      try {
        await checkHealth();
        setStatus("connected");
      } catch {
        setStatus("disconnected");
      }
    };

    checkConnection();

    // Check connection periodically
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>IRIS</h1>
        <div className="status">
          <span className={`status-dot ${status}`}></span>
          <span>
            {status === "connected" && "Connected"}
            {status === "connecting" && "Connecting..."}
            {status === "disconnected" && "Offline"}
          </span>
        </div>
      </header>

      <Chat />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
