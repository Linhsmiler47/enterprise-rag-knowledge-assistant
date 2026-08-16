"use client";

import { useEffect, useState } from "react";
import {
  DocumentSummary,
  deleteDocument,
  listDocuments,
  triggerIngest,
} from "@/lib/api";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }

  // Inlined (not a call to `refresh`) so state updates stay tied to this effect's own
  // cleanup/cancellation, per react-hooks/set-state-in-effect.
  useEffect(() => {
    let cancelled = false;
    listDocuments()
      .then((docs) => {
        if (!cancelled) {
          setDocuments(docs);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load documents.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleIngest(id: number) {
    setBusyId(id);
    try {
      await triggerIngest(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id: number) {
    setBusyId(id);
    try {
      await deleteDocument(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <h1>Documents</h1>
      {error && <p className="error">{error}</p>}
      {loading ? (
        <p className="muted">Loading...</p>
      ) : documents.length === 0 ? (
        <p className="muted">No documents yet -- go to Upload.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Chunks</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.original_filename}</td>
                <td>
                  <span className={`status status-${doc.status}`}>{doc.status}</span>
                  {doc.ingestion_error && (
                    <div className="error">{doc.ingestion_error}</div>
                  )}
                </td>
                <td>{doc.chunk_count}</td>
                <td>{doc.source}</td>
                <td>
                  {doc.status !== "ingested" && (
                    <button
                      onClick={() => handleIngest(doc.id)}
                      disabled={busyId === doc.id}
                    >
                      Ingest
                    </button>
                  )}{" "}
                  <button onClick={() => handleDelete(doc.id)} disabled={busyId === doc.id}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
