import { supabase } from './supabase'
import { MenuItem } from '@/types'
import { UserConstraints, checkSafety } from './safety_engine'

// Helper to calculate Jaccard Similarity between two sets of ingredients
function calculateSimilarity(ingredientsA: string[], ingredientsB: string[]): number {
    const setA = new Set(ingredientsA.map(i => i.toLowerCase()))
    const setB = new Set(ingredientsB.map(i => i.toLowerCase()))

    const intersection = new Set([...setA].filter(x => setB.has(x)))
    const union = new Set([...setA, ...setB])

    if (union.size === 0) return 0
    return intersection.size / union.size
}

export async function getSafeRecommendations(constraints: UserConstraints): Promise<MenuItem[]> {
    // Reuse safety engine logic to get safe items
    const result = await checkSafety(constraints)
    return result.safeItems
}

export async function getSimilarItems(itemId: string): Promise<MenuItem[]> {
    // 1. Fetch the target item's ingredients
    const { data: targetItem, error: targetError } = await supabase
        .from('menu_items')
        .select(`
            *,
            item_ingredients (ingredient_name)
        `)
        .eq('id', itemId)
        .single()

    if (targetError || !targetItem) {
        console.error('Error fetching target item:', targetError)
        return []
    }

    const targetIngredients = targetItem.item_ingredients?.map((i: any) => i.ingredient_name) || []

    // 2. Fetch all other items
    const { data: allItems, error: allError } = await supabase
        .from('menu_items')
        .select(`
            *,
            item_ingredients (ingredient_name)
        `)
        .neq('id', itemId) // Exclude self

    if (allError || !allItems) return []

    // 3. Calculate similarity and rank
    const rankedItems = allItems.map((item: any) => {
        const ingredients = item.item_ingredients?.map((i: any) => i.ingredient_name) || []
        const score = calculateSimilarity(targetIngredients, ingredients)
        return {
            ...item,
            ingredients, // Attach ingredients for UI if needed
            similarityScore: score
        }
    })
        .filter((item: any) => item.similarityScore > 0) // Filter out totally unrelated items
        .sort((a: any, b: any) => b.similarityScore - a.similarityScore)
        .slice(0, 5) // Top 5

    return rankedItems
}
