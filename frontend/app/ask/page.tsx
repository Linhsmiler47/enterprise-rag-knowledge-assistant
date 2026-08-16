"use client";

import { useState } from "react";
import { QueryResponse, askQuestion } from "@/lib/api";

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await askQuestion(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Ask a question</h1>
      <form onSubmit={handleSubmit}>
        <textarea
          rows={3}
          placeholder="e.g. How often are database backups taken?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <p>
          <button type="submit" disabled={loading || !question.trim()}>
            {loading ? "Asking..." : "Ask"}
          </button>
        </p>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div>
          <p>
            <span className={`status ${result.grounded ? "status-ingested" : "status-failed"}`}>
              {result.grounded ? "grounded" : "insufficient evidence"}
            </span>
          </p>
          <p>{result.answer}</p>
          {result.citations.length > 0 && (
            <>
              <h3>Citations</h3>
              <ul>
                {result.citations.map((c, i) => (
                  <li key={i}>
                    {c.document} (chunk #{c.chunk_id}) -- similarity {c.similarity.toFixed(2)}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
