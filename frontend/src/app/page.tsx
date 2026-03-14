import HeroSection from '@/components/home/HeroSection'
import FeaturesSection from '@/components/home/FeaturesSection'
import HowItWorksSection from '@/components/home/HowItWorksSection'
import ChatDemoSection from '@/components/home/ChatDemoSection'
import FinalCtaSection from '@/components/home/FinalCtaSection'
import HomepageFooter from '@/components/home/HomepageFooter'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface text-slate-900">
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <ChatDemoSection />
      <FinalCtaSection />
      <HomepageFooter />
    </div>
  )
}
