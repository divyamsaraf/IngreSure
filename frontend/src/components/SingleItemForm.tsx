'use client';

import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Chip,
  Typography,
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';

const ALLERGENS = [
  'Peanuts', 'Tree Nuts', 'Milk', 'Egg', 'Wheat', 'Soy', 'Fish', 'Shellfish', 'Sesame'
];

const DIET_TYPES = [
  'Vegan', 'Vegetarian', 'Gluten-Free', 'Halal', 'Kosher', 'Keto', 'Paleo'
];

export default function SingleItemForm() {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    ingredients: '',
    allergens: [] as string[],
    dietTypes: [] as string[],
    price: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (event: SelectChangeEvent<string[]>) => {
    const {
      target: { value, name },
    } = event;
    setFormData((prev) => ({
      ...prev,
      [name]: typeof value === 'string' ? value.split(',') : value,
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form Data:', formData);
    // TODO: Send to API
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      maxWidth: 700,
      mx: 'auto',
      p: 5,
      bgcolor: 'background.paper',
      borderRadius: 4,
      boxShadow: '0 10px 40px -10px rgba(0,0,0,0.1)'
    }}>
      <Box sx={{ textAlign: 'center', mb: 2 }}>
        <Typography variant="h4" component="h2" gutterBottom sx={{ fontWeight: 700, color: 'primary.main' }}>
          Add Menu Item
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Enter the details of your dish to get AI-powered tags.
        </Typography>
      </Box>

      <TextField
        label="Item Name"
        name="name"
        value={formData.name}
        onChange={handleChange}
        required
        fullWidth
        variant="outlined"
        placeholder="e.g. Truffle Mushroom Risotto"
      />

      <TextField
        label="Description"
        name="description"
        value={formData.description}
        onChange={handleChange}
        multiline
        rows={4}
        fullWidth
        placeholder="Describe the dish, flavors, and textures..."
      />

      <TextField
        label="Ingredients"
        name="ingredients"
        value={formData.ingredients}
        onChange={handleChange}
        helperText="Separate ingredients with commas (e.g., Arborio Rice, Mushrooms, Parmesan)"
        fullWidth
      />

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
        <FormControl fullWidth>
          <InputLabel>Allergens</InputLabel>
          <Select
            multiple
            name="allergens"
            value={formData.allergens}
            onChange={handleSelectChange}
            input={<OutlinedInput label="Allergens" />}
            renderValue={(selected) => (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selected.map((value) => (
                  <Chip key={value} label={value} size="small" color="error" variant="outlined" />
                ))}
              </Box>
            )}
          >
            {ALLERGENS.map((allergen) => (
              <MenuItem key={allergen} value={allergen}>
                {allergen}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl fullWidth>
          <InputLabel>Dietary Types</InputLabel>
          <Select
            multiple
            name="dietTypes"
            value={formData.dietTypes}
            onChange={handleSelectChange}
            input={<OutlinedInput label="Dietary Types" />}
            renderValue={(selected) => (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selected.map((value) => (
                  <Chip key={value} label={value} size="small" color="success" variant="outlined" />
                ))}
              </Box>
            )}
          >
            {DIET_TYPES.map((diet) => (
              <MenuItem key={diet} value={diet}>
                {diet}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <TextField
        label="Price"
        name="price"
        type="number"
        value={formData.price}
        onChange={handleChange}
        InputProps={{ startAdornment: <Typography sx={{ mr: 1, color: 'text.secondary' }}>$</Typography> }}
        fullWidth
        sx={{ maxWidth: 200 }}
      />

      <Button variant="contained" type="submit" size="large" sx={{ mt: 2, py: 1.5, fontSize: '1.1rem' }}>
        Submit Item
      </Button>
    </Box>
  );
}
