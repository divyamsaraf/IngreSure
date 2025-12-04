import Link from 'next/link'
import { ArrowRight, CheckCircle, ShieldCheck, Search } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section */}
      <header className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white py-20 px-6">
        <div className="container mx-auto max-w-5xl text-center">
          <h1 className="text-5xl font-bold mb-6 leading-tight">
            Eat with Confidence.<br />Know What's Inside.
          </h1>
          <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
            IngreSure uses AI to verify menu ingredients, detect allergens, and ensure your food matches your dietary needs.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/chat" className="bg-white text-blue-600 px-8 py-3 rounded-full font-bold hover:bg-gray-100 transition-colors flex items-center gap-2">
              Try Chat Assistant <ArrowRight className="w-5 h-5" />
            </Link>
            <Link href="/dashboard" className="bg-transparent border-2 border-white text-white px-8 py-3 rounded-full font-bold hover:bg-white/10 transition-colors">
              For Restaurants
            </Link>
          </div>
        </div>
      </header>

      {/* Features Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto max-w-6xl">
          <h2 className="text-3xl font-bold text-center mb-16 text-gray-800">Why Choose IngreSure?</h2>

          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center p-6 rounded-xl bg-blue-50">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6 text-blue-600">
                <ShieldCheck className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold mb-3">AI Verification</h3>
              <p className="text-gray-600">
                Our Mistral 7B powered engine cross-references menu descriptions with ingredient lists to catch inconsistencies.
              </p>
            </div>

            <div className="text-center p-6 rounded-xl bg-green-50">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6 text-green-600">
                <CheckCircle className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold mb-3">Safety First</h3>
              <p className="text-gray-600">
                Rule-based safety engine ensures allergen and diet checks are based on facts, not hallucinations.
              </p>
            </div>

            <div className="text-center p-6 rounded-xl bg-purple-50">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6 text-purple-600">
                <Search className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold mb-3">Smart Search</h3>
              <p className="text-gray-600">
                Find exactly what you can eat. Filter by diet, allergen, or ingredients with our intelligent recommendation system.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gray-900 text-white py-20 px-6 text-center">
        <div className="container mx-auto">
          <h2 className="text-3xl font-bold mb-6">Ready to dine safely?</h2>
          <Link href="/recommendations" className="bg-blue-600 text-white px-8 py-3 rounded-full font-bold hover:bg-blue-700 transition-colors inline-block">
            Find Safe Food Now
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-100 py-8 text-center text-gray-500 text-sm">
        <p>&copy; {new Date().getFullYear()} IngreSure. All rights reserved.</p>
      </footer>
    </div>
  )
}
