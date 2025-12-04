import { supabase } from './supabase'
import { MenuItem } from '@/types'

export interface SafetyResult {
    isSafe: boolean
    reason: string
    safeItems: MenuItem[]
}

export interface UserConstraints {
    allergens: string[]
    diets: string[]
    query?: string
}

export async function searchMenuItems(query: string): Promise<MenuItem[]> {
    // In a real app, we would use Supabase Vector Search here.
    // For MVP, we'll do a simple text search on name/description.
    const { data, error } = await supabase
        .from('menu_items')
        .select(`
            *,
            item_ingredients (ingredient_name, is_allergen),
            tag_history (tags)
        `)
        .ilike('name', `%${query}%`)

    if (error) {
        console.error('Error searching menu items:', error)
        return []
    }

    // Transform data to match MenuItem interface
    return data.map((item) => ({
        ...item,
        ingredients: item.item_ingredients?.map((i: { ingredient_name: string }) => i.ingredient_name) || [],
        allergens: item.item_ingredients?.filter((i: { is_allergen: boolean }) => i.is_allergen).map((i: { ingredient_name: string }) => i.ingredient_name) || [],
        dietary_tags: item.tag_history?.[0]?.tags || [] // Assuming latest tags
    })) as MenuItem[]
}

export async function checkSafety(constraints: UserConstraints): Promise<SafetyResult> {
    // 1. Fetch all items (or filter by query if provided)
    let items: MenuItem[] = []
    if (constraints.query) {
        items = await searchMenuItems(constraints.query)
    } else {
        // Fetch all if no specific query (e.g. "Show me vegan items")
        // Limiting to 50 for MVP performance
        const { data, error } = await supabase
            .from('menu_items')
            .select(`
                *,
                item_ingredients (ingredient_name, is_allergen),
                tag_history (tags)
            `)
            .limit(50)

        if (!error && data) {
            items = data.map((item) => ({
                ...item,
                ingredients: item.item_ingredients?.map((i: { ingredient_name: string }) => i.ingredient_name) || [],
                allergens: item.item_ingredients?.filter((i: { is_allergen: boolean }) => i.is_allergen).map((i: { ingredient_name: string }) => i.ingredient_name) || [],
                dietary_tags: item.tag_history?.[0]?.tags || []
            })) as MenuItem[]
        }
    }

    // 2. Filter based on constraints
    const safeItems = items.filter(item => {
        // Check Allergens
        const hasAllergen = constraints.allergens.some(allergen =>
            item.allergens?.some(a => a.toLowerCase().includes(allergen.toLowerCase())) ||
            item.ingredients?.some(i => i.toLowerCase().includes(allergen.toLowerCase()))
        )
        if (hasAllergen) return false

        // Check Diets
        const hasDiet = constraints.diets.every(diet =>
            item.dietary_tags?.some(tag => tag.toLowerCase() === diet.toLowerCase())
        )
        if (!hasDiet && constraints.diets.length > 0) return false

        return true
    })

    return {
        isSafe: safeItems.length > 0,
        reason: safeItems.length > 0
            ? `Found ${safeItems.length} safe items matching your criteria.`
            : "No items found matching your safety criteria.",
        safeItems
    }
}
