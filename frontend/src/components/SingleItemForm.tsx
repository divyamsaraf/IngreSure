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
    <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 3, maxWidth: 600, mx: 'auto', p: 3, bgcolor: 'background.paper', borderRadius: 2, boxShadow: 1 }}>
      <Typography variant="h6" gutterBottom>
        Add Menu Item
      </Typography>

      <TextField
        label="Item Name"
        name="name"
        value={formData.name}
        onChange={handleChange}
        required
        fullWidth
      />

      <TextField
        label="Description"
        name="description"
        value={formData.description}
        onChange={handleChange}
        multiline
        rows={3}
        fullWidth
      />

      <TextField
        label="Ingredients (comma separated)"
        name="ingredients"
        value={formData.ingredients}
        onChange={handleChange}
        helperText="e.g., Chicken, Rice, Salt, Pepper"
        fullWidth
      />

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
                <Chip key={value} label={value} />
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
                <Chip key={value} label={value} />
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

      <TextField
        label="Price"
        name="price"
        type="number"
        value={formData.price}
        onChange={handleChange}
        InputProps={{ startAdornment: <Typography sx={{ mr: 1 }}>$</Typography> }}
        fullWidth
      />

      <Button variant="contained" type="submit" size="large">
        Submit Item
      </Button>
    </Box>
  );
}
