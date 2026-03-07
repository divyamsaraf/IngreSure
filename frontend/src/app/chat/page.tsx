import ChatInterface from '@/components/chat/ChatInterface'

export default function ChatPage() {
    return (
        <div className="h-[calc(100vh-64px)] overflow-hidden flex justify-center bg-slate-50">
            <div className="w-full max-w-3xl flex flex-col flex-1 min-h-0 px-2 py-2 md:px-4 md:py-4">
                <ChatInterface
                    apiEndpoint="/api/chat?mode=grocery"
                    title="Grocery Safety Assistant"
                    subtitle="AI-powered ingredient checker"
                    suggestions={[
                        "Ingredients: Sugar, Gelatin, Water. Is this Halal?",
                        "I am Jain. Can I eat potato chips?",
                        "Sugar, Milk, Egg, Gelatin, Soy, Wheat, Peanut, Tree Nuts, Fish?"
                    ]}
                />
            </div>
        </div>
    )
}
