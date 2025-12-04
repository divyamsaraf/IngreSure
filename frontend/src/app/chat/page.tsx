import ChatInterface from '@/components/chat/ChatInterface'

export default function ChatPage() {
    return (
        <div className="container mx-auto p-6 max-w-4xl">
            <h1 className="text-3xl font-bold mb-8 text-center">Consumer Chat</h1>
            <ChatInterface />
        </div>
    )
}
