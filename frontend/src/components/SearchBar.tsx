'use client';

import React, { useState, useEffect } from 'react';
import { TextField, InputAdornment } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

interface SearchBarProps {
    onSearch: (query: string) => void;
}

export default function SearchBar({ onSearch }: SearchBarProps) {
    const [query, setQuery] = useState('');

    useEffect(() => {
        const delayDebounceFn = setTimeout(() => {
            onSearch(query);
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [query, onSearch]);

    return (
        <TextField
            fullWidth
            variant="outlined"
            placeholder="Search for food, ingredients..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            InputProps={{
                startAdornment: (
                    <InputAdornment position="start">
                        <SearchIcon sx={{ color: 'text.secondary', fontSize: 28 }} />
                    </InputAdornment>
                ),
                sx: {
                    borderRadius: 4,
                    bgcolor: 'background.paper',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
                    fontSize: '1.1rem',
                    py: 1.5,
                    px: 2,
                    '& fieldset': { border: 'none' }, // Cleaner look
                }
            }}
        />
    );
}
