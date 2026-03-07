import ChatInterface from '@/components/chat/ChatInterface'

export default function RestaurantChatPage() {
    return (
        <div className="h-[calc(100vh-64px)] overflow-hidden flex justify-center bg-slate-50">
            <div className="w-full max-w-3xl flex flex-col flex-1 min-h-0 px-2 py-2 md:px-4 md:py-4">
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
        </div>
    )
}
