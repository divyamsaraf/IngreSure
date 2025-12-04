'use client';

import React, { useState } from 'react';
import { Box, Container, Tab, Tabs, Typography, Paper } from '@mui/material';
import SingleItemForm from '@/components/SingleItemForm';
import CSVUpload from '@/components/CSVUpload';

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function CustomTabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`simple-tabpanel-${index}`}
            aria-labelledby={`simple-tab-${index}`}
            {...other}
        >
            {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
        </div>
    );
}

export default function UploadPage() {
    const [value, setValue] = useState(0);

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setValue(newValue);
    };

    return (
        <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ fontWeight: 'bold', mb: 4 }}>
                Restaurant Menu Upload
            </Typography>

            <Paper sx={{ width: '100%' }}>
                <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Tabs value={value} onChange={handleChange} aria-label="upload tabs" centered>
                        <Tab label="Single Item" />
                        <Tab label="Bulk Upload (CSV)" />
                    </Tabs>
                </Box>
                <CustomTabPanel value={value} index={0}>
                    <SingleItemForm />
                </CustomTabPanel>
                <CustomTabPanel value={value} index={1}>
                    <CSVUpload />
                </CustomTabPanel>
            </Paper>
        </Container>
    );
}
