'use client';

import React from 'react';
import { Box, Typography, FormGroup, FormControlLabel, Checkbox, Divider } from '@mui/material';

const DIET_TYPES = ['Vegan', 'Vegetarian', 'Gluten-Free', 'Halal', 'Keto'];
const ALLERGENS = ['Peanuts', 'Tree Nuts', 'Milk', 'Egg', 'Wheat', 'Soy', 'Fish', 'Shellfish'];

interface SearchFiltersProps {
    selectedDiets: string[];
    selectedAllergens: string[];
    onDietChange: (diet: string, checked: boolean) => void;
    onAllergenChange: (allergen: string, checked: boolean) => void;
}

export default function SearchFilters({
    selectedDiets,
    selectedAllergens,
    onDietChange,
    onAllergenChange,
}: SearchFiltersProps) {
    return (
        <Box sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
                Filters
            </Typography>

            <Typography variant="subtitle1" sx={{ mt: 2, fontWeight: 'bold' }}>
                Dietary Preferences
            </Typography>
            <FormGroup>
                {DIET_TYPES.map((diet) => (
                    <FormControlLabel
                        key={diet}
                        control={
                            <Checkbox
                                checked={selectedDiets.includes(diet)}
                                onChange={(e) => onDietChange(diet, e.target.checked)}
                            />
                        }
                        label={diet}
                    />
                ))}
            </FormGroup>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                Exclude Allergens
            </Typography>
            <FormGroup>
                {ALLERGENS.map((allergen) => (
                    <FormControlLabel
                        key={allergen}
                        control={
                            <Checkbox
                                checked={selectedAllergens.includes(allergen)}
                                onChange={(e) => onAllergenChange(allergen, e.target.checked)}
                            />
                        }
                        label={allergen}
                    />
                ))}
            </FormGroup>
        </Box>
    );
}
