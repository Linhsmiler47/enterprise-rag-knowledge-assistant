import Link from "next/link";

export default function HomePage() {
  return (
    <div>
      <h1>Enterprise RAG Knowledge Assistant</h1>
      <p className="muted">
        Upload internal documents, ingest them, and ask grounded questions with citations.
      </p>
      <ol>
        <li>
          <Link href="/upload">Upload</Link> a document (.md or .txt)
        </li>
        <li>
          Go to <Link href="/documents">Documents</Link> and trigger ingestion
        </li>
        <li>
          <Link href="/ask">Ask</Link> a question and inspect the citations
        </li>
      </ol>
    </div>
  );
}
