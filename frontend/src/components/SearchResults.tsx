'use client';

import React from 'react';
import { Box, Card, CardContent, Typography, Chip, Grid } from '@mui/material';

interface MenuItem {
    id: string;
    name: string;
    description: string;
    price: number;
    restaurant_id: string;
    similarity: number;
    rank: number;
}

interface SearchResultsProps {
    results: MenuItem[];
    loading: boolean;
}

export default function SearchResults({ results, loading }: SearchResultsProps) {
    if (loading) {
        return <Typography>Loading...</Typography>;
    }

    if (results.length === 0) {
        return <Typography>No results found.</Typography>;
    }

    return (
        <Grid container spacing={2}>
            {results.map((item) => (
                <Grid size={{ xs: 12 }} key={item.id}>
                    <Card variant="outlined">
                        <CardContent>
                            <Typography variant="h6" component="div">
                                {item.name}
                            </Typography>
                            <Typography sx={{ mb: 1.5 }} color="text.secondary">
                                ${item.price}
                            </Typography>
                            <Typography variant="body2">
                                {item.description}
                            </Typography>
                            <Box sx={{ mt: 1 }}>
                                <Chip label={`Match: ${(item.similarity * 100).toFixed(0)}%`} size="small" color="primary" variant="outlined" />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            ))}
        </Grid>
    );
}
