'use client'

import React, { useState, useEffect } from 'react'
import { getSafeRecommendations, getSimilarItems } from '@/lib/recommendation_engine'
import RecommendationList from '@/components/recommendations/RecommendationList'
import { MenuItem } from '@/types'
import { Loader2 } from 'lucide-react'

export default function RecommendationsPage() {
    const [safeItems, setSafeItems] = useState<MenuItem[]>([])
    const [similarItems, setSimilarItems] = useState<MenuItem[]>([])
    const [loading, setLoading] = useState(true)
    const [selectedDiet, setSelectedDiet] = useState<string>('Vegan') // Default for demo

    useEffect(() => {
        fetchRecommendations()
    }, [selectedDiet])

    const fetchRecommendations = async () => {
        setLoading(true)
        try {
            // 1. Fetch Safe Recommendations
            const safe = await getSafeRecommendations({
                allergens: [], // Could be dynamic
                diets: [selectedDiet]
            })
            setSafeItems(safe)

            // 2. Fetch Similar Items (Demo: pick first safe item if exists)
            if (safe.length > 0) {
                const similar = await getSimilarItems(safe[0].id)
                setSimilarItems(similar)
            } else {
                setSimilarItems([])
            }
        } catch (error) {
            console.error('Error fetching recommendations:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container mx-auto p-6 max-w-6xl">
            <h1 className="text-3xl font-bold mb-6">For You</h1>

            {/* Controls */}
            <div className="mb-8 flex gap-4 items-center bg-white p-4 rounded-lg shadow-sm border">
                <label className="font-medium">Dietary Preference:</label>
                <select
                    value={selectedDiet}
                    onChange={(e) => setSelectedDiet(e.target.value)}
                    className="border rounded px-3 py-1"
                >
                    <option value="Vegan">Vegan</option>
                    <option value="Vegetarian">Vegetarian</option>
                    <option value="Gluten-Free">Gluten-Free</option>
                    <option value="Halal">Halal</option>
                </select>
            </div>

            {loading ? (
                <div className="flex justify-center p-12">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                </div>
            ) : (
                <>
                    <RecommendationList
                        title={`Safe for ${selectedDiet} Diet`}
                        items={safeItems}
                    />

                    {safeItems.length > 0 && (
                        <RecommendationList
                            title={`Because you might like "${safeItems[0].name}"`}
                            items={similarItems}
                            emptyMessage="No similar items found."
                        />
                    )}
                </>
            )}
        </div>
    )
}
