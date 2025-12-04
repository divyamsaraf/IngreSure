'use client'

import { useState, useRef } from 'react'
import {
    Box,
    Container,
    Typography,
    Button,
    Paper,
    CircularProgress,
    Card,
    CardContent,
    Grid,
    Chip,
    Alert
} from '@mui/material'
import { Camera, Upload, RefreshCw, Check, X, AlertTriangle } from 'lucide-react'

interface DietaryStatus {
    status: 'green' | 'yellow' | 'red'
    reason: string
}

interface ScanResult {
    raw_text: string
    ingredients: string[]
    dietary_scorecard: Record<string, DietaryStatus>
    confidence_scores: { overall: number }
}

export default function ScannerPage() {
    const [image, setImage] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<ScanResult | null>(null)
    const [error, setError] = useState<string | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (file) {
            const reader = new FileReader()
            reader.onload = (e) => setImage(e.target?.result as string)
            reader.readAsDataURL(file)
            processImage(file)
        }
    }

    const processImage = async (file: File) => {
        setLoading(true)
        setError(null)
        setResult(null)

        try {
            const formData = new FormData()
            formData.append('file', file)

            // Call Python API directly (assuming proxy or CORS allowed)
            // In production, use Next.js API route to proxy to Python service
            const response = await fetch('http://localhost:8000/scan', {
                method: 'POST',
                body: formData,
            })

            if (!response.ok) throw new Error('Scan failed')

            const data = await response.json()
            setResult(data)
        } catch (err) {
            setError('Failed to process image. Please try again.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'green': return 'success'
            case 'yellow': return 'warning'
            case 'red': return 'error'
            default: return 'default'
        }
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'green': return <Check size={16} />
            case 'yellow': return <AlertTriangle size={16} />
            case 'red': return <X size={16} />
            default: return null
        }
    }

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            <Typography variant="h4" gutterBottom fontWeight="bold" color="primary">
                Visual Dietary Scanner
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Take a photo of the ingredients list to instantly check for dietary compliance.
            </Typography>

            {/* Upload Area */}
            <Paper
                variant="outlined"
                sx={{
                    p: 4,
                    textAlign: 'center',
                    borderStyle: 'dashed',
                    borderColor: 'divider',
                    bgcolor: 'background.default',
                    mb: 4
                }}
            >
                {image ? (
                    <Box position="relative">
                        <img src={image} alt="Uploaded" style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8 }} />
                        <Button
                            variant="contained"
                            color="secondary"
                            size="small"
                            startIcon={<RefreshCw size={16} />}
                            onClick={() => { setImage(null); setResult(null); }}
                            sx={{ position: 'absolute', top: 10, right: 10 }}
                        >
                            Retake
                        </Button>
                    </Box>
                ) : (
                    <Box>
                        <Camera size={48} color="#666" style={{ marginBottom: 16 }} />
                        <Typography gutterBottom>
                            Drag & drop or click to upload photo
                        </Typography>
                        <input
                            type="file"
                            accept="image/*"
                            hidden
                            ref={fileInputRef}
                            onChange={handleFileUpload}
                        />
                        <Button
                            variant="contained"
                            startIcon={<Upload size={18} />}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            Upload Photo
                        </Button>
                    </Box>
                )}
            </Paper>

            {/* Loading State */}
            {loading && (
                <Box textAlign="center" py={4}>
                    <CircularProgress />
                    <Typography mt={2} color="text.secondary">
                        Analyzing ingredients... (OCR + AI)
                    </Typography>
                </Box>
            )}

            {/* Error State */}
            {error && (
                <Alert severity="error" sx={{ mb: 4 }}>
                    {error}
                </Alert>
            )}

            {/* Results */}
            {result && (
                <Box>
                    <Typography variant="h5" gutterBottom fontWeight="bold">
                        Dietary Scorecard
                    </Typography>

                    <Grid container spacing={2} mb={4}>
                        {Object.entries(result.dietary_scorecard).map(([diet, info]) => (
                            <Grid item xs={12} sm={6} md={4} key={diet}>
                                <Card variant="outlined" sx={{
                                    borderColor: `${getStatusColor(info.status)}.main`,
                                    borderWidth: 2
                                }}>
                                    <CardContent>
                                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                                            <Chip
                                                label={diet}
                                                color={getStatusColor(info.status) as any}
                                                size="small"
                                                icon={getStatusIcon(info.status)!}
                                            />
                                        </Box>
                                        <Typography variant="body2" color="text.secondary">
                                            {info.reason}
                                        </Typography>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>

                    <Paper variant="outlined" sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>
                            Detected Ingredients
                        </Typography>
                        <Box display="flex" flexWrap="wrap" gap={1}>
                            {result.ingredients.map((ing, idx) => (
                                <Chip key={idx} label={ing} variant="outlined" />
                            ))}
                        </Box>
                        <Typography variant="caption" display="block" mt={2} color="text.secondary">
                            Raw Text: {result.raw_text.substring(0, 100)}...
                        </Typography>
                    </Paper>
                </Box>
            )}
        </Container>
    )
}
