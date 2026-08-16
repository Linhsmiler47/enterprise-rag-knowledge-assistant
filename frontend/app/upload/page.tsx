"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { uploadDocument } from "@/lib/api";

export default function UploadPage() {
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleUpload(file: File) {
    setStatus("uploading");
    setMessage(null);
    try {
      const document = await uploadDocument(file);
      setStatus("done");
      setMessage(`Uploaded "${document.original_filename}" -- status: ${document.status}.`);
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  return (
    <div>
      <h1>Upload a document</h1>
      <p className="muted">Markdown (.md) or plain text (.txt) only.</p>

      <input
        ref={inputRef}
        type="file"
        accept=".md,.txt"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUpload(file);
        }}
      />

      {status === "uploading" && <p className="muted">Uploading...</p>}
      {status === "done" && (
        <p>
          {message} Go to <Link href="/documents">Documents</Link> to trigger ingestion.
        </p>
      )}
      {status === "error" && <p className="error">{message}</p>}
    </div>
  );
}
