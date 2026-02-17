'use client';

import React, { useState } from 'react';
import { Container, Grid, Typography, Box } from '@mui/material';
import SearchBar from '@/components/SearchBar';
import SearchFilters from '@/components/SearchFilters';
import SearchResults, { SearchMenuItem } from '@/components/SearchResults';

export default function SearchPage() {
    const [results, setResults] = useState<SearchMenuItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedDiets, setSelectedDiets] = useState<string[]>([]);
    const [selectedAllergens, setSelectedAllergens] = useState<string[]>([]);

    const handleSearch = async (query: string) => {
        setLoading(true);
        try {
            // TODO: Replace with real Supabase global-search edge function call
            console.log('Searching for:', query, 'Filters:', { selectedDiets, selectedAllergens });
            await new Promise(resolve => setTimeout(resolve, 1000));
            setResults([]);
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
