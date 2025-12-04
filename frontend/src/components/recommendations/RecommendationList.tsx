import React from 'react'
import { MenuItem } from '@/types'
import { Star, AlertCircle } from 'lucide-react'

interface Props {
    title: string
    items: MenuItem[]
    emptyMessage?: string
}

export default function RecommendationList({ title, items, emptyMessage = "No items found." }: Props) {
    return (
        <div className="mb-8">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Star className="text-yellow-500 w-5 h-5" />
                {title}
            </h2>

            {items.length === 0 ? (
                <div className="text-gray-500 italic p-4 bg-gray-50 rounded-lg">
                    {emptyMessage}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {items.map((item) => (
                        <div key={item.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-white">
                            <div className="flex justify-between items-start">
                                <h3 className="font-semibold text-lg">{item.name}</h3>
                                <span className="font-medium text-green-600">${item.price}</span>
                            </div>
                            <p className="text-gray-600 text-sm mt-1 line-clamp-2">{item.description}</p>

                            {/* Tags */}
                            <div className="mt-3 flex flex-wrap gap-2">
                                {item.dietary_tags?.map(tag => (
                                    <span key={tag} className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                                        {tag}
                                    </span>
                                ))}
                                {item.allergens?.map(allergen => (
                                    <span key={allergen} className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full flex items-center gap-1">
                                        <AlertCircle className="w-3 h-3" /> {allergen}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
