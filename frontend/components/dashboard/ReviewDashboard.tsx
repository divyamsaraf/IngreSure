'use client'

import React, { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { MenuItem, VerificationLog } from '@/types'
import { VerificationStatus } from './VerificationStatus'

export default function ReviewDashboard() {
    const [items, setItems] = useState<MenuItem[]>([])
    const [logs, setLogs] = useState<Record<string, VerificationLog>>({})
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        try {
            const { data: menuItems, error: itemsError } = await supabase
                .from('menu_items')
                .select('*')
                .order('created_at', { ascending: false })

            if (itemsError) throw itemsError

            const { data: verificationLogs, error: logsError } = await supabase
                .from('verification_logs')
                .select('*')

            if (logsError) throw logsError

            const logsMap = verificationLogs.reduce((acc, log) => {
                acc[log.menu_item_id] = log
                return acc
            }, {} as Record<string, VerificationLog>)

            setItems(menuItems || [])
            setLogs(logsMap)
        } catch (error) {
            console.error('Error fetching data:', error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) return <div>Loading...</div>

    return (
        <div className="container mx-auto p-6">
            <h1 className="text-2xl font-bold mb-6">Menu Item Review</h1>
            <div className="grid gap-6">
                {items.map((item) => (
                    <div key={item.id} className="border p-4 rounded-lg bg-gray-50">
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <h2 className="text-xl font-semibold">{item.name}</h2>
                                <p className="text-gray-600">{item.description}</p>
                                <p className="font-medium mt-1">${item.price}</p>
                            </div>
                            <div className="text-sm text-gray-500">
                                {new Date(item.created_at).toLocaleDateString()}
                            </div>
                        </div>

                        <div className="mt-4">
                            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">AI Verification</h3>
                            {logs[item.id] ? (
                                <VerificationStatus log={logs[item.id]} />
                            ) : (
                                <div className="text-gray-400 italic">Pending verification...</div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
