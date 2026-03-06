import HeroSection from '@/components/home/HeroSection'
import FeaturesSection from '@/components/home/FeaturesSection'
import ChatDemoSection from '@/components/home/ChatDemoSection'
import HomepageFooter from '@/components/home/HomepageFooter'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900">
      <HeroSection />
      <FeaturesSection />
      <ChatDemoSection />
      <HomepageFooter />
    </div>
  )
}
