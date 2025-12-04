'use client';

import React, { useState } from 'react';
import { Box, Typography, Paper, Button, List, ListItem, ListItemText } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

export default function CSVUpload() {
    const [file, setFile] = useState<File | null>(null);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    const handleUpload = () => {
        if (!file) return;
        console.log('Uploading file:', file.name);
        // TODO: Implement CSV parsing and upload logic
    };

    return (
        <Box sx={{ maxWidth: 600, mx: 'auto', p: 3 }}>
            <Paper
                variant="outlined"
                sx={{
                    p: 5,
                    borderStyle: 'dashed',
                    textAlign: 'center',
                    cursor: 'pointer',
                    bgcolor: 'background.default',
                    '&:hover': { bgcolor: 'action.hover' },
                }}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
            >
                <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                    Drag & Drop CSV here
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                    or click to select a file
                </Typography>
                <input
                    type="file"
                    accept=".csv"
                    hidden
                    id="csv-upload-input"
                    onChange={handleFileChange}
                />
                <label htmlFor="csv-upload-input">
                    <Button variant="outlined" component="span" sx={{ mt: 2 }}>
                        Select File
                    </Button>
                </label>
            </Paper>

            {file && (
                <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle1">Selected File:</Typography>
                    <List>
                        <ListItem>
                            <ListItemText primary={file.name} secondary={`${(file.size / 1024).toFixed(2)} KB`} />
                        </ListItem>
                    </List>
                    <Button variant="contained" fullWidth onClick={handleUpload} sx={{ mt: 2 }}>
                        Upload CSV
                    </Button>
                </Box>
            )}
        </Box>
    );
}
