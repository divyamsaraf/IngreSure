'use client';

import React, { useState } from 'react';
import { Container, Grid, Typography, Box } from '@mui/material';
import SearchBar from '@/components/SearchBar';
import SearchFilters from '@/components/SearchFilters';
import SearchResults from '@/components/SearchResults';

// Define types locally or import from a shared types file
interface MenuItem {
    id: string;
    name: string;
    description: string;
    price: number;
    restaurant_id: string;
    similarity: number;
    rank: number;
}

export default function SearchPage() {
    const [results, setResults] = useState<MenuItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedDiets, setSelectedDiets] = useState<string[]>([]);
    const [selectedAllergens, setSelectedAllergens] = useState<string[]>([]);

    const handleSearch = async (query: string) => {
        setLoading(true);
        try {
            // In a real app, use the Supabase client or fetch directly
            // const supabase = createClientComponentClient();
            // const { data } = await supabase.functions.invoke('global-search', { ... });

            // Mocking the API call for now since we don't have the full environment set up
            console.log('Searching for:', query, 'Filters:', { selectedDiets, selectedAllergens });

            // Simulate network delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Mock results
            const mockResults: MenuItem[] = [
                {
                    id: '1',
                    name: 'Vegan Burger',
                    description: 'Plant-based patty with lettuce and tomato.',
                    price: 12.99,
                    restaurant_id: 'r1',
                    similarity: 0.95,
                    rank: 1
                },
                {
                    id: '2',
                    name: 'Gluten-Free Pizza',
                    description: 'Cauliflower crust with cheese and basil.',
                    price: 15.50,
                    restaurant_id: 'r2',
                    similarity: 0.88,
                    rank: 2
                }
            ];
            setResults(mockResults);

        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDietChange = (diet: string, checked: boolean) => {
        setSelectedDiets(prev =>
            checked ? [...prev, diet] : prev.filter(d => d !== diet)
        );
    };

    const handleAllergenChange = (allergen: string, checked: boolean) => {
        setSelectedAllergens(prev =>
            checked ? [...prev, allergen] : prev.filter(a => a !== allergen)
        );
    };

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ fontWeight: 'bold', mb: 4 }}>
                Global Search
            </Typography>

            <Box sx={{ mb: 4 }}>
                <SearchBar onSearch={handleSearch} />
            </Box>

            <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 3 }}>
                    <SearchFilters
                        selectedDiets={selectedDiets}
                        selectedAllergens={selectedAllergens}
                        onDietChange={handleDietChange}
                        onAllergenChange={handleAllergenChange}
                    />
                </Grid>
                <Grid size={{ xs: 12, md: 9 }}>
                    <SearchResults results={results} loading={loading} />
                </Grid>
            </Grid>
        </Container>
    );
}
