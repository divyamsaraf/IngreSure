'use client';

import React from 'react';
import { Box, Card, CardContent, Typography, Chip, Grid, Skeleton } from '@mui/material';

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
        return (
            <Grid container spacing={3}>
                {[1, 2, 3].map((i) => (
                    <Grid size={{ xs: 12 }} key={i}>
                        <Skeleton variant="rectangular" height={160} sx={{ borderRadius: 4 }} />
                    </Grid>
                ))}
            </Grid>
        );
    }

    if (results.length === 0) {
        return (
            <Box sx={{ textAlign: 'center', py: 8 }}>
                <Typography variant="h6" color="text.secondary">
                    No results found. Try adjusting your filters.
                </Typography>
            </Box>
        );
    }

    return (
        <Grid container spacing={3}>
            {results.map((item) => (
                <Grid size={{ xs: 12 }} key={item.id}>
                    <Card sx={{
                        transition: 'transform 0.2s, box-shadow 0.2s',
                        '&:hover': {
                            transform: 'translateY(-4px)',
                            boxShadow: '0 12px 40px rgba(0,0,0,0.1)'
                        }
                    }}>
                        <CardContent sx={{ p: 3 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                                    {item.name}
                                </Typography>
                                <Typography variant="h6" color="primary.main" sx={{ fontWeight: 700 }}>
                                    ${item.price}
                                </Typography>
                            </Box>

                            <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                                {item.description}
                            </Typography>

                            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                <Chip
                                    label={`Match: ${(item.similarity * 100).toFixed(0)}%`}
                                    size="small"
                                    color={item.similarity > 0.8 ? "success" : "warning"}
                                    variant="filled"
                                    sx={{ fontWeight: 600 }}
                                />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            ))}
        </Grid>
    );
}
