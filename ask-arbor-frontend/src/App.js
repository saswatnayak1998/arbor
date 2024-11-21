import React, { useState } from "react";
import "./App.css";

const App = () => {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleQueryChange = (e) => {
    setQuery(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!query.trim()) {
      alert("Please enter a query!");
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch("http://0.0.0.0:5000/process_query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) {
        throw new Error("Failed to fetch response. Please try again.");
      }

      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <div className="container">
        <div className="header">
          <h1>Ask Arbor</h1>
        </div>
        <form className="form-section" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Enter your query..."
            value={query}
            onChange={handleQueryChange}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Loading..." : "Submit"}
          </button>
        </form>
        <div className="response-container">
          {error && (
            <div className="error-section">
              <p>{error}</p>
            </div>
          )}
          {response && (
            <div className="response-section">
              <h2 className="response-title">Response</h2>
              <div className="response-content">
                <pre>
                  {`
Context:
  ${response.context || "Not available"}

Relevant Products:
  ${response.relevant_products?.join(", ") || "Not available"}

Relevant Documents:
  ${response.relevant_documents?.join(", ") || "Not available"}

Key Points:
  - ${response.key_points?.join("\n  - ") || "Not available"}

Answer:
  ${response.answer || "Not available"}
                  `}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
