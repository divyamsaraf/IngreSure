import ChatInterface from '@/components/chat/ChatInterface'

export default function RestaurantChatPage() {
    return (
        <div className="flex flex-col min-h-[calc(100vh-4rem)] md:min-h-[calc(100vh-5rem)] px-4 py-4 md:py-6">
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
