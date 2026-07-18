import HeroSection from '@/components/home/HeroSection'
import ChatDemoSection from '@/components/home/ChatDemoSection'
import HowVerdictWorksSection from '@/components/home/HowVerdictWorksSection'
import BusinessBridgeSection from '@/components/home/BusinessBridgeSection'
import FinalCtaSection from '@/components/home/FinalCtaSection'
import HomepageFooter from '@/components/home/HomepageFooter'

/**
 * Surgical trust refresh landing.
 * To restore the previous design:
 *   export { default } from '@/components/home/legacy/LandingPage'
 */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface text-slate-900">
      <HeroSection />
      <ChatDemoSection />
      <HowVerdictWorksSection />
      <BusinessBridgeSection />
      <FinalCtaSection />
      <HomepageFooter />
    </div>
  )
}
