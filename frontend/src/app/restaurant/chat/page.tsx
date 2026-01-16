import ChatInterface from '@/components/chat/ChatInterface'

export default function RestaurantChatPage() {
    return (
        <div className="container mx-auto max-w-2xl p-4 md:py-8 min-h-screen">
            <ChatInterface
                apiEndpoint="/api/chat?mode=restaurant"
                title="Restaurant Menu Assistant"
                subtitle="Search menus and find safe options"
                suggestions={[
                    "Show me vegan options at Burger King",
                    "What is safe for nut allergy at Starbucks?",
                    "Any gluten-free pasta nearby?"
                ]}
            />
        </div>
    )
}
