import { AlertTriangle, RotateCcw } from 'lucide-react'
export default function ErrorMessage({ message, onRetry }) { return message ? <div className="error-banner" role="alert"><AlertTriangle size={18} /><span>{message}</span><button onClick={onRetry}><RotateCcw size={15} /> Retry</button></div> : null }
