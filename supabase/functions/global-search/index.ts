
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// Mock embedding function (replace with actual API call to OpenAI/Mistral)
async function generateEmbedding(text: string): Promise<number[]> {
    // This is a placeholder. In production, call your embedding model.
    // Returning random vector for demonstration.
    return Array(384).fill(0).map(() => Math.random());
}

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

        const { query, filters } = await req.json();
        const { dietary, allergens } = filters || {};

        // 1. Generate Embedding for the query
        const embedding = await generateEmbedding(query);

        // 2. Call the RPC function for hybrid search
        const { data: results, error } = await supabase
            .rpc('search_menu_items', {
                query_text: query,
                query_embedding: embedding,
                match_threshold: 0.5, // Adjust as needed
                match_count: 20,
                filter_dietary: dietary && dietary.length > 0 ? dietary : null,
                filter_allergens: allergens && allergens.length > 0 ? allergens : null,
            });

        if (error) throw error;

        return new Response(
            JSON.stringify({ results }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );

    } catch (error) {
        return new Response(
            JSON.stringify({ error: error.message }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
    }
});
