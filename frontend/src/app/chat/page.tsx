import ChatInterface from '@/components/chat/ChatInterface'

export default function ChatPage() {
    return (
        <div className="container mx-auto max-w-2xl p-4 md:py-8 min-h-screen">
            <ChatInterface
                apiEndpoint="/api/chat?mode=grocery"
                title="Grocery Safety Assistant"
                subtitle="Deterministic Compliance Engine"
                suggestions={[
                    "Ingredients: Sugar, Gelatin, Water. Is this Halal?",
                    "I am Jain. Can I eat potato chips?",
                    "Check these ingredients for gluten..."
                ]}
            />
        </div>
    )
}
