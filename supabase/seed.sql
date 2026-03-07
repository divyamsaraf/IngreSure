-- Seed data. Menu/restaurant tables removed; only users (auth/demo) seeded.

INSERT INTO auth.users (id, email)
VALUES ('d0d8c19c-3b36-4423-8f5d-8e3607c2d6c6', 'demo@ingresure.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.users (id, name, email, diet_type)
VALUES ('d0d8c19c-3b36-4423-8f5d-8e3607c2d6c6', 'Demo User', 'demo@ingresure.com', 'Omnivore')
ON CONFLICT (id) DO NOTHING;
