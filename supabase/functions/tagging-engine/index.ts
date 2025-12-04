
export interface TaggingResult {
    tags: string[];
    allergens: string[];
    warnings: string[];
}

const RULES = [
    {
        tag: 'Vegan',
        forbidden: ['chicken', 'beef', 'pork', 'fish', 'egg', 'milk', 'cheese', 'honey', 'butter', 'cream', 'yogurt', 'whey', 'casein', 'gelatin', 'lard'],
    },
    {
        tag: 'Vegetarian',
        forbidden: ['chicken', 'beef', 'pork', 'fish', 'shellfish', 'gelatin', 'lard'],
    },
    {
        tag: 'Gluten-Free',
        forbidden: ['wheat', 'barley', 'rye', 'malt', 'brewer\'s yeast', 'seitan'],
    },
    {
        tag: 'Dairy-Free',
        forbidden: ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'whey', 'casein', 'lactose'],
    },
];

const ALLERGEN_RULES = [
    { allergen: 'Peanuts', keywords: ['peanut'] },
    { allergen: 'Tree Nuts', keywords: ['almond', 'cashew', 'walnut', 'pecan', 'pistachio', 'macadamia', 'hazelnut'] },
    { allergen: 'Milk', keywords: ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'whey', 'casein'] },
    { allergen: 'Egg', keywords: ['egg', 'albumin'] },
    { allergen: 'Wheat', keywords: ['wheat', 'flour', 'gluten'] },
    { allergen: 'Soy', keywords: ['soy', 'tofu', 'tempeh', 'edamame'] },
    { allergen: 'Fish', keywords: ['fish', 'salmon', 'tuna', 'cod', 'tilapia'] },
    { allergen: 'Shellfish', keywords: ['shrimp', 'crab', 'lobster', 'prawn', 'clam', 'mussel', 'oyster'] },
    { allergen: 'Sesame', keywords: ['sesame', 'tahini'] },
];

export function analyzeIngredients(ingredients: string[]): TaggingResult {
    const lowerIngredients = ingredients.map(i => i.toLowerCase());
    const tags: string[] = [];
    const allergens: string[] = [];
    const warnings: string[] = [];

    // Check Diet Tags
    for (const rule of RULES) {
        const hasForbidden = lowerIngredients.some(ing =>
            rule.forbidden.some(forbidden => ing.includes(forbidden))
        );
        if (!hasForbidden) {
            tags.push(rule.tag);
        }
    }

    // Check Allergens
    for (const rule of ALLERGEN_RULES) {
        const hasAllergen = lowerIngredients.some(ing =>
            rule.keywords.some(keyword => ing.includes(keyword))
        );
        if (hasAllergen) {
            allergens.push(rule.allergen);
        }
    }

    return { tags, allergens, warnings };
}
