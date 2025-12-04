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

interface Ingredient {
    ingredient_name: string;
}

interface MenuItemWithIngredients extends MenuItem {
    item_ingredients: Ingredient[];
    similarityScore?: number;
}

export async function getSimilarItems(itemId: string): Promise<MenuItem[]> {
    // 1. Fetch the target item's ingredients
    const { data: targetItemData, error: targetError } = await supabase
        .from('menu_items')
        .select(`
            *,
            item_ingredients (ingredient_name)
        `)
        .eq('id', itemId)
        .single()

    if (targetError || !targetItemData) {
        console.error('Error fetching target item:', targetError)
        return []
    }

    const targetItem = targetItemData as unknown as MenuItemWithIngredients;
    const targetIngredients = targetItem.item_ingredients?.map(i => i.ingredient_name) || []

    // 2. Fetch all other items
    const { data: allItemsData, error: allError } = await supabase
        .from('menu_items')
        .select(`
            *,
            item_ingredients (ingredient_name)
        `)
        .neq('id', itemId) // Exclude self

    if (allError || !allItemsData) return []

    const allItems = allItemsData as unknown as MenuItemWithIngredients[];

    // 3. Calculate similarity and rank
    const rankedItems = allItems.map((item) => {
        const ingredients = item.item_ingredients?.map(i => i.ingredient_name) || []
        const score = calculateSimilarity(targetIngredients, ingredients)
        return {
            ...item,
            ingredients, // Attach ingredients for UI if needed
            similarityScore: score
        }
    })
        .filter((item) => (item.similarityScore || 0) > 0) // Filter out totally unrelated items
        .sort((a, b) => (b.similarityScore || 0) - (a.similarityScore || 0))
        .slice(0, 5) // Top 5

    return rankedItems
}
