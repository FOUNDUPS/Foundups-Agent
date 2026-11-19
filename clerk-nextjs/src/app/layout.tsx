import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import {
  ClerkProvider,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from "@clerk/nextjs";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Foundups | Alpha",
  description: "Peer-to-Peer Autonomous Venture System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[#08080f] text-white min-h-screen`}
        >
          {/* Header with auth buttons */}
          <header className="fixed top-0 left-0 right-0 z-50 flex justify-between items-center p-4 bg-[#08080f]/80 backdrop-blur-md border-b border-white/10">
            <Link href="/" className="text-xl font-bold">
              Found<span className="text-[#7c5cfc]">UPS</span>
            </Link>
            <nav className="flex items-center gap-4">
              <SignedOut>
                <SignInButton mode="modal">
                  <button className="px-4 py-2 text-sm hover:text-[#7c5cfc] transition">
                    Sign In
                  </button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <button className="px-4 py-2 text-sm bg-[#7c5cfc] rounded-lg hover:bg-[#6b4ce0] transition">
                    Get Started
                  </button>
                </SignUpButton>
              </SignedOut>
              <SignedIn>
                <a href="/member" className="px-4 py-2 text-sm hover:text-[#7c5cfc] transition">
                  Dashboard
                </a>
                <UserButton afterSignOutUrl="/" />
              </SignedIn>
            </nav>
          </header>

          {/* Main content with padding for fixed header */}
          <main className="pt-20">
            {children}
          </main>
        </body>
      </html>
    </ClerkProvider>
  );
}
