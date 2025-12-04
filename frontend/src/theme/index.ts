'use client';

import { createTheme } from '@mui/material/styles';
import { Inter, Playfair_Display } from 'next/font/google';

const inter = Inter({
    weight: ['300', '400', '500', '700'],
    subsets: ['latin'],
    display: 'swap',
});

const playfair = Playfair_Display({
    weight: ['400', '700'],
    subsets: ['latin'],
    display: 'swap',
});

const theme = createTheme({
    typography: {
        fontFamily: inter.style.fontFamily,
        h1: {
            fontFamily: playfair.style.fontFamily,
            fontWeight: 700,
        },
        h2: {
            fontFamily: playfair.style.fontFamily,
            fontWeight: 700,
        },
        h3: {
            fontFamily: playfair.style.fontFamily,
            fontWeight: 700,
        },
        h4: {
            fontFamily: playfair.style.fontFamily,
            fontWeight: 700,
        },
        h5: {
            fontFamily: playfair.style.fontFamily,
            fontWeight: 700,
        },
        h6: {
            fontFamily: playfair.style.fontFamily,
            fontWeight: 700,
        },
    },
    palette: {
        primary: {
            main: '#0F172A', // Deep Slate Blue (Premium/Trust)
            light: '#334155',
            dark: '#020617',
            contrastText: '#ffffff',
        },
        secondary: {
            main: '#10B981', // Emerald Green (Freshness/Safety)
            light: '#34D399',
            dark: '#059669',
            contrastText: '#ffffff',
        },
        background: {
            default: '#F8FAFC', // Very light slate gray
            paper: '#ffffff',
        },
        text: {
            primary: '#1E293B',
            secondary: '#64748B',
        },
        error: {
            main: '#EF4444',
        },
        warning: {
            main: '#F59E0B',
        },
        success: {
            main: '#10B981',
        },
        info: {
            main: '#3B82F6',
        },
    },
    shape: {
        borderRadius: 12,
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    textTransform: 'none',
                    fontWeight: 600,
                    borderRadius: '8px',
                    padding: '10px 24px',
                    boxShadow: 'none',
                    '&:hover': {
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                    },
                },
                containedPrimary: {
                    background: 'linear-gradient(135deg, #0F172A 0%, #334155 100%)',
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: '16px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
                    border: '1px solid rgba(0,0,0,0.05)',
                },
            },
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        borderRadius: '12px',
                    },
                },
            },
        },
        MuiChip: {
            styleOverrides: {
                root: {
                    fontWeight: 500,
                    borderRadius: '8px',
                },
            },
        },
    },
});

export default theme;
