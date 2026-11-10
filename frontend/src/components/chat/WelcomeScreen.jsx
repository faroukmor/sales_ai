import { BadgePercent, GitCompareArrows, Laptop, WandSparkles } from 'lucide-react'
const prompts = [
  [Laptop, 'Find a laptop under 100000 DA'],
  [GitCompareArrows, 'Compare two laptops'],
  [WandSparkles, 'Recommend a PC for programming'],
  [BadgePercent, 'Show available promotions'],
]
export default function WelcomeScreen({ onPrompt }) {
  return <section className="welcome"><div className="welcome-icon"><WandSparkles /></div><p className="chat-eyebrow">GEANT AI SHOPPING</p>
    <h2>Welcome to GEANT Chat UI</h2><p>Your intelligent AI shopping assistant.</p>
    <div className="prompt-grid">{prompts.map(([Icon, label]) => <button key={label} onClick={() => onPrompt(label)}><Icon size={19} /><span>{label}</span></button>)}</div>
    <p className="demo-warning">Catalog products and promotions are demonstration data.</p>
  </section>
}
