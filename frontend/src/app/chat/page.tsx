import ChatInterface from '@/components/chat/ChatInterface'

export default function ChatPage() {
    return (
        <div className="flex flex-col min-h-[calc(100vh-4rem)] md:min-h-[calc(100vh-5rem)] px-4 py-4 md:py-6">
            <ChatInterface
                apiEndpoint="/api/chat?mode=grocery"
                title="Grocery Safety Assistant"
                subtitle="AI & rule-based ingredient checker"
                suggestions={[
                    "Ingredients: Sugar, Gelatin, Water. Is this Halal?",
                    "I am Jain. Can I eat potato chips?",
                    "Check these ingredients for gluten..."
                ]}
            />
        </div>
    )
}
