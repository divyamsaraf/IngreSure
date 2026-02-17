'use client'

import React from 'react'
import Link from 'next/link'
import { ShieldCheck, ArrowRight } from 'lucide-react'

export default function Navbar() {
    return (
        <nav className="bg-white border-b border-gray-100 py-4 px-6 sticky top-0 z-50 shadow-sm">
            <div className="container mx-auto flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2 group">
                    <div className="bg-blue-600 p-2 rounded-lg group-hover:bg-blue-700 transition-colors">
                        <ShieldCheck className="w-6 h-6 text-white" />
                    </div>
                    <span className="font-bold text-xl text-gray-900 tracking-tight">IngreSure</span>
                </Link>

                <div className="hidden md:flex items-center gap-8 font-medium text-gray-600">
                    <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
                    <Link href="/chat" className="hover:text-blue-600 transition-colors">Grocery Assistant</Link>
                </div>

                <div className="flex items-center gap-4">
                    <Link href="/chat" className="bg-blue-600 text-white px-5 py-2 rounded-full font-bold text-sm hover:bg-blue-700 transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20">
                        Start Audit <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            </div>
        </nav>
    )
}
