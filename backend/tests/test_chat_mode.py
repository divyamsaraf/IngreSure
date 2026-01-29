import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add 'ai' directory to path so imports like 'from dietary_rules' work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ai')))

from rag_service import RAGService
from dietary_rules import DietaryRuleEngine

class TestChatMode(unittest.TestCase):
    def setUp(self):
        # Mock env vars to avoid 'credentials missing' warning in RAGService init
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://example.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'fake-key'
        }):
            with patch('rag_service.SentenceTransformer') as MockEmbed:
                self.rag_service = RAGService()
                self.rag_service.supabase = MagicMock()
                self.rag_service.generate_embedding = MagicMock(return_value=[0.1]*384)

    def test_filter_extraction(self):
        """Test if DietaryRuleEngine extracts filters correctly."""
        query = "Do you have any vegan options without nuts?"
        filters = DietaryRuleEngine.extract_filters(query)
        self.assertIn("Vegan", filters["dietary"])
        self.assertTrue(any(a in filters["allergens"] for a in ["Peanuts", "Tree Nuts"]))

    def test_retrieve_with_filters(self):
        """Test if retrieve passes filters to RPC."""
        query = "Show me vegan dishes"
        self.rag_service.retrieve(query)
        
        # Verify RPC call args
        args = self.rag_service.supabase.rpc.call_args
        self.assertIsNotNone(args)
        rpc_name = args[0][0]
        rpc_params = args[0][1]
        
        self.assertEqual(rpc_name, 'search_menu_items')
        self.assertEqual(rpc_params['filter_dietary'], ['Vegan'])
        self.assertIsNone(rpc_params['filter_allergens'])

    def test_retrieve_with_allergen_filters(self):
        """Test if retrieve passes allergen filters to RPC."""
        query = "I am allergic to peanuts"
        self.rag_service.retrieve(query)
        
        # Verify RPC call args
        args = self.rag_service.supabase.rpc.call_args
        rpc_params = args[0][1]
        
        self.assertIn("Peanuts", rpc_params['filter_allergens'])

    @patch('rag_service.requests.post')
    def test_persona_prompt(self, mock_post):
        """Test if the system prompt contains the Restaurant Persona."""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [b'{"response": "Hello", "done": false}', b'{"response": "", "done": true}']
        mock_post.return_value.__enter__.return_value = mock_response
        
        context = [{"name": "Salad", "description": "Green salad", "price": 10}]
        generator = self.rag_service.generate_answer_stream("Hi", context)
        list(generator) # Consume
        
        # Check the prompt sent to Ollama
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        prompt = payload['prompt']
        
        self.assertIn("You are a friendly and helpful waiter", prompt)
        self.assertIn("Menu Context:", prompt)
        self.assertIn("Salad", prompt)

if __name__ == '__main__':
    unittest.main()
