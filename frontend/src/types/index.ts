export interface MenuItem {
    id: string
    restaurant_id: string
    name: string
    description: string
    price: number
    currency: string
    is_available: boolean
    created_at: string
    // Joined fields for safety checks
    ingredients?: string[]
    allergens?: string[]
    dietary_tags?: string[]
}

export interface VerificationLog {
    id: string
    menu_item_id: string
    is_consistent: boolean
    confidence_score: number
    issues: string[]
    suggested_corrections: Record<string, any>
    verified_at: string
}
