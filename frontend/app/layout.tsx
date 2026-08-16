import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Enterprise RAG Knowledge Assistant",
  description: "Upload documents, ask grounded questions, inspect citations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav>
          <Link href="/upload">Upload</Link>
          <Link href="/documents">Documents</Link>
          <Link href="/ask">Ask</Link>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
