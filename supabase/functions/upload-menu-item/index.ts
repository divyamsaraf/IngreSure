
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { analyzeIngredients } from "../tagging-engine/index.ts";

const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders });
    }

    try {
        const supabase = createClient(
            Deno.env.get('SUPABASE_URL') ?? '',
            Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
        );

        const { name, description, ingredients, price, restaurant_id } = await req.json();

        // 1. Analyze Ingredients
        const ingredientList = ingredients.split(',').map((i: string) => i.trim());
        const { tags, allergens } = analyzeIngredients(ingredientList);

        // 2. Insert into menu_items
        const { data: menuItem, error: menuError } = await supabase
            .from('menu_items')
            .insert([
                { name, description, price, restaurant_id }
            ])
            .select()
            .single();

        if (menuError) throw menuError;

        // 3. Insert into item_ingredients
        const ingredientInserts = ingredientList.map((ing: string) => ({
            menu_item_id: menuItem.id,
            ingredient_name: ing,
        }));

        const { error: ingError } = await supabase
            .from('item_ingredients')
            .insert(ingredientInserts);

        if (ingError) throw ingError;

        // 4. Insert into tag_history
        const { error: tagError } = await supabase
            .from('tag_history')
            .insert([
                {
                    menu_item_id: menuItem.id,
                    tags: tags,
                    allergens: allergens,
                    source: 'auto-tagging',
                    confidence_score: 1.0,
                }
            ]);

        if (tagError) throw tagError;

        return new Response(
            JSON.stringify({ message: 'Item uploaded successfully', menuItem, tags, allergens }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );

    } catch (error) {
        return new Response(
            JSON.stringify({ error: error.message }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
    }
});
