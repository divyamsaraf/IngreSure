-- Seed Data

-- 1. Create a sample user (Restaurant Owner)
-- Note: In real Supabase, users are in auth.users. 
-- For local dev, we can insert into public.users if we disable FK constraint or insert into auth.users first.
-- Ideally, we just insert into public.users and assume the auth user exists or we mock it.
-- However, public.users references auth.users.
-- Let's try to insert a dummy user into auth.users first (only works if we have permissions, which we do in local).

INSERT INTO auth.users (id, email)
VALUES ('d0d8c19c-3b36-4423-8f5d-8e3607c2d6c6', 'demo@ingresure.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.users (id, name, email, diet_type)
VALUES ('d0d8c19c-3b36-4423-8f5d-8e3607c2d6c6', 'Demo Restaurant', 'demo@ingresure.com', 'Omnivore')
ON CONFLICT (id) DO NOTHING;

-- 2. Insert Menu Items
INSERT INTO public.menu_items (id, restaurant_id, name, description, price, is_available)
VALUES 
('11111111-1111-1111-1111-111111111111', 'd0d8c19c-3b36-4423-8f5d-8e3607c2d6c6', 'Vegan Buddha Bowl', 'Quinoa, roasted chickpeas, avocado, and tahini dressing.', 12.99, true),
('22222222-2222-2222-2222-222222222222', 'd0d8c19c-3b36-4423-8f5d-8e3607c2d6c6', 'Classic Cheeseburger', 'Beef patty, cheddar cheese, lettuce, tomato, brioche bun.', 14.50, true),
('33333333-3333-3333-3333-333333333333', 'd0d8c19c-3b36-4423-8f5d-8e3607c2d6c6', 'Chicken Tikka Masala', 'Grilled chicken in creamy tomato curry sauce.', 16.00, true)
ON CONFLICT (id) DO NOTHING;

-- 3. Insert Ingredients
INSERT INTO public.item_ingredients (menu_item_id, ingredient_name, is_allergen)
VALUES
('11111111-1111-1111-1111-111111111111', 'Quinoa', false),
('11111111-1111-1111-1111-111111111111', 'Chickpeas', false),
('11111111-1111-1111-1111-111111111111', 'Avocado', false),
('11111111-1111-1111-1111-111111111111', 'Tahini', true), -- Sesame

('22222222-2222-2222-2222-222222222222', 'Beef', false),
('22222222-2222-2222-2222-222222222222', 'Cheddar Cheese', true), -- Dairy
('22222222-2222-2222-2222-222222222222', 'Wheat Bun', true), -- Gluten

('33333333-3333-3333-3333-333333333333', 'Chicken', false),
('33333333-3333-3333-3333-333333333333', 'Cream', true), -- Dairy
('33333333-3333-3333-3333-333333333333', 'Tomato', false);

-- 4. Insert Tag History (Simulate Auto-Tagging)
INSERT INTO public.tag_history (menu_item_id, tags, allergens, source)
VALUES
('11111111-1111-1111-1111-111111111111', '["Vegan", "Vegetarian", "Gluten-Free"]', '["Sesame"]', 'auto-tagging'),
('22222222-2222-2222-2222-222222222222', '["Non-Vegetarian"]', '["Dairy", "Gluten"]', 'auto-tagging'),
('33333333-3333-3333-3333-333333333333', '["Non-Vegetarian", "Halal"]', '["Dairy"]', 'auto-tagging');
