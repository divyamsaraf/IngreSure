import React from 'react'
import { VerificationLog } from '@/types'
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react'

interface Props {
    log: VerificationLog
}

export const VerificationStatus: React.FC<Props> = ({ log }) => {
    if (!log) return null

    return (
        <div className="p-4 border rounded-lg shadow-sm bg-white">
            <div className="flex items-center gap-2 mb-2">
                {log.is_consistent ? (
                    <CheckCircle className="text-green-500" />
                ) : (
                    <AlertTriangle className="text-yellow-500" />
                )}
                <h3 className="font-semibold">
                    Verification Result ({Math.round(log.confidence_score * 100)}% Confidence)
                </h3>
            </div>

            {!log.is_consistent && (
                <div className="mt-2">
                    <h4 className="text-sm font-medium text-gray-700">Issues Found:</h4>
                    <ul className="list-disc list-inside text-sm text-red-600">
                        {log.issues.map((issue, idx) => (
                            <li key={idx}>{issue}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    )
}
