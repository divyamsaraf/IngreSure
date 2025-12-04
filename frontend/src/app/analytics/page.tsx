'use client'

import React, { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Loader2, AlertTriangle, CheckCircle, FileText } from 'lucide-react'

export default function AnalyticsPage() {
    const [stats, setStats] = useState({
        totalItems: 0,
        verifiedItems: 0,
        issuesFound: 0
    })
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchStats()
    }, [])

    const fetchStats = async () => {
        try {
            // 1. Total Items
            const { count: total } = await supabase
                .from('menu_items')
                .select('*', { count: 'exact', head: true })

            // 2. Verified Items (Items with logs)
            const { count: verified } = await supabase
                .from('verification_logs')
                .select('*', { count: 'exact', head: true })

            // 3. Issues Found (Logs where is_consistent is false)
            const { count: issues } = await supabase
                .from('verification_logs')
                .select('*', { count: 'exact', head: true })
                .eq('is_consistent', false)

            setStats({
                totalItems: total || 0,
                verifiedItems: verified || 0,
                issuesFound: issues || 0
            })
        } catch (error) {
            console.error('Error fetching stats:', error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) return <div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>

    return (
        <div className="container mx-auto p-6 max-w-6xl">
            <h1 className="text-3xl font-bold mb-8">Restaurant Analytics</h1>

            <div className="grid md:grid-cols-3 gap-6 mb-12">
                <div className="bg-white p-6 rounded-xl shadow-sm border">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-blue-100 text-blue-600 rounded-lg">
                            <FileText className="w-6 h-6" />
                        </div>
                        <h3 className="text-gray-500 font-medium">Total Menu Items</h3>
                    </div>
                    <p className="text-3xl font-bold">{stats.totalItems}</p>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-sm border">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-green-100 text-green-600 rounded-lg">
                            <CheckCircle className="w-6 h-6" />
                        </div>
                        <h3 className="text-gray-500 font-medium">Verified Items</h3>
                    </div>
                    <p className="text-3xl font-bold">{stats.verifiedItems}</p>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-sm border">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-red-100 text-red-600 rounded-lg">
                            <AlertTriangle className="w-6 h-6" />
                        </div>
                        <h3 className="text-gray-500 font-medium">Issues Detected</h3>
                    </div>
                    <p className="text-3xl font-bold">{stats.issuesFound}</p>
                </div>
            </div>

            {/* Placeholder for Charts */}
            <div className="bg-white p-6 rounded-xl shadow-sm border h-64 flex items-center justify-center text-gray-400">
                Chart Visualization (Coming Soon)
            </div>
        </div>
    )
}
