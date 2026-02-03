import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Expert Suitability Engine',
  description: 'Discover and rank YouTube tech experts for consulting engagements',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950">
        {/* Ambient background effects */}
        <div className="fixed inset-0 -z-10 overflow-hidden">
          <div className="absolute top-0 -left-1/4 w-1/2 h-1/2 bg-ocean-600/20 rounded-full blur-[128px]" />
          <div className="absolute bottom-0 -right-1/4 w-1/2 h-1/2 bg-ocean-900/30 rounded-full blur-[128px]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-gradient-radial from-ocean-950/50 to-transparent" />
        </div>
        
        {children}
      </body>
    </html>
  )
}

