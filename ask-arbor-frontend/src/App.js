import React, { useState } from "react";
import "./App.css";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [isResponseVisible, setResponseVisible] = useState(false); 
  const [isLoading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!query.trim()) {
      alert("Please enter a query!");
      return;
    }

    setLoading(true);
    setResponseVisible(false);

    try {
      const res = await fetch("http://0.0.0.0:5000/process_query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) throw new Error("Failed to fetch response.");

      const data = await res.json();

      const output = `
Context:
  ${data.context || "Not available"}

Relevant Products:
  ${data.relevant_products.join(", ") || "Not available"}

Relevant Documents:
  ${data.relevant_documents.join(", ") || "Not available"}

Key Points:
  - ${data.key_points.join("\n  - ") || "Not available"}

Answer:
  ${data.answer || "Not available"}
      `;

      setResponse(output.trim());
      setResponseVisible(true); // Show the response after loading
    } catch (error) {
      setResponse(`Error: ${error.message}`);
      setResponseVisible(true); // Show the error response
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>Ask Arbor</h1>
      </div>
      <div className="form-section">
        <input
          type="text"
          placeholder="Enter your query..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={handleSubmit} disabled={isLoading}>
          {isLoading ? "Loading..." : "Submit"}
        </button>
      </div>
      {isResponseVisible && ( 
        <div className="response-section">
          <h2 className="response-title">Response</h2>
          <div className="response-content">{response}</div>
        </div>
      )}
    </div>
  );
}

export default App;
