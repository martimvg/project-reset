import './globals.css';
import type { Metadata, Viewport } from 'next';
import { StoreProvider } from '@/lib/store';
import Header from '@/components/Header';

export const metadata: Metadata = {
  title: 'Applicant Desk',
  description: 'Every entry-level investment banking and private equity role in London, your applications, AI-tailored CVs and interview prep.',
};
export const viewport: Viewport = { width: 'device-width', initialScale: 1, viewportFit: 'cover' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&display=swap" />
      </head>
      <body>
        <StoreProvider>
          <Header />
          <main className="wrap">{children}</main>
        </StoreProvider>
      </body>
    </html>
  );
}
