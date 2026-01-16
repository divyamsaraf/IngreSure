'use client'

import React, { useState, useEffect } from 'react'
import { X, Check, ChevronRight, AlertCircle, Edit2 } from 'lucide-react'
import { UserProfile, DEFAULT_PROFILE, DietType } from '@/types/userProfile'

interface OnboardingModalProps {
    isOpen: boolean
    onClose: () => void
    onSave: (profile: UserProfile) => void
    initialProfile?: UserProfile
}

export default function OnboardingModal({ isOpen, onClose, onSave, initialProfile }: OnboardingModalProps) {
    const [step, setStep] = useState(1)
    const [profile, setProfile] = useState<UserProfile>(initialProfile || DEFAULT_PROFILE)
    const [customAllergy, setCustomAllergy] = useState('')

    // Reset state when opening
    useEffect(() => {
        if (isOpen) {
            setStep(1)
            setProfile(initialProfile ? { ...initialProfile, allergies: initialProfile.allergies || [] } : DEFAULT_PROFILE)
        }
    }, [isOpen, initialProfile])

    if (!isOpen) return null

    const handleDietSelect = (diet: DietType) => {
        let updates: Partial<UserProfile> = { diet }

        // Dynamic Branching Logic
        if (diet === 'Vegan') {
            updates.dairy_allowed = false
            updates.meat_allowed = false
        } else if (diet === 'Jain') {
            updates.meat_allowed = false
            updates.dairy_allowed = true // Jains consume dairy usually
        } else if (diet === 'Hindu Veg') {
            updates.meat_allowed = false
            updates.dairy_allowed = true
        } else if (diet === 'Vegetarian') {
            updates.meat_allowed = false
            updates.dairy_allowed = true
        }

        setProfile(prev => ({ ...prev, ...updates }))
    }

    const toggleAllergy = (allergen: string) => {
        setProfile(prev => {
            const current = prev.allergies || []
            if (current.includes(allergen)) {
                return { ...prev, allergies: current.filter(a => a !== allergen) }
            } else {
                return { ...prev, allergies: [...current, allergen] }
            }
        })
    }

    const handleComplete = () => {
        const finalProfile = { ...profile, is_onboarding_completed: true }
        onSave(finalProfile)
        onClose()
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-6 text-white relative">
                    <button
                        onClick={onClose}
                        className="absolute right-4 top-4 p-2 hover:bg-white/10 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                    <h2 className="text-2xl font-bold mb-2">Help me check food correctly</h2>
                    <p className="text-blue-100 text-sm">Optional — takes under 10 seconds.</p>

                    {/* Progress Bar */}
                    <div className="flex gap-2 mt-6">
                        {[1, 2, 3, 4].map(s => (
                            <div
                                key={s}
                                className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${s <= step ? 'bg-white' : 'bg-white/20'
                                    }`}
                            />
                        ))}
                    </div>
                </div>

                {/* Body */}
                <div className="p-6 min-h-[300px]">

                    {/* STEP 1: DIET */}
                    {step === 1 && (
                        <div className="space-y-4 animate-in slide-in-from-right-8 duration-300">
                            <h3 className="text-xl font-bold text-gray-800">Do you follow any specific diet?</h3>
                            <p className="text-gray-500 text-sm">This helps avoid ingredients you don’t eat.</p>

                            <div className="grid grid-cols-2 gap-3 mt-4">
                                {[
                                    "Hindu Veg", "Hindu Non-Veg",
                                    "Jain", "Vegan",
                                    "Halal", "Kosher",
                                    "Vegetarian", "No specific rules"
                                ].map((option) => (
                                    <button
                                        key={option}
                                        onClick={() => handleDietSelect(option)}
                                        className={`p-4 rounded-xl border-2 text-left transition-all ${profile.diet === option
                                            ? 'border-blue-600 bg-blue-50 text-blue-700 font-bold shadow-sm'
                                            : 'border-slate-100 hover:border-blue-200 hover:bg-slate-50 text-slate-700'
                                            }`}
                                    >
                                        {option}
                                    </button>
                                ))}
                            </div>


                            <div className="pt-6 flex justify-end">
                                <button
                                    onClick={() => {
                                        if (profile.diet === 'Vegan') {
                                            setStep(3)
                                        } else {
                                            setStep(2)
                                        }
                                    }}
                                    className="bg-blue-600 text-white px-6 py-2 rounded-full font-bold hover:bg-blue-700 flex items-center gap-2 transition-all shadow-lg shadow-blue-600/20"
                                >
                                    Next <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 2: DAIRY & MEAT */}
                    {step === 2 && (
                        <div className="space-y-6 animate-in slide-in-from-right-8 duration-300">
                            <h3 className="text-xl font-bold text-gray-800">Dietary Preferences</h3>

                            {/* Dairy Question */}
                            <div className="space-y-3">
                                <p className="font-medium text-gray-700">Do you consume milk / dairy?</p>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => setProfile(p => ({ ...p, dairy_allowed: true }))}
                                        className={`flex-1 p-3 rounded-lg border-2 transition-all ${profile.dairy_allowed ? 'border-green-500 bg-green-50 text-green-700 font-bold' : 'border-slate-100'
                                            }`}
                                    >
                                        Yes
                                    </button>
                                    <button
                                        onClick={() => setProfile(p => ({ ...p, dairy_allowed: false }))}
                                        className={`flex-1 p-3 rounded-lg border-2 transition-all ${!profile.dairy_allowed ? 'border-red-500 bg-red-50 text-red-700 font-bold' : 'border-slate-100'
                                            }`}
                                    >
                                        No
                                    </button>
                                </div>
                            </div>

                            {/* Meat Question (Only if not already implied by diet) */}
                            {!['Hindu Veg', 'Jain', 'Vegetarian'].includes(profile.diet) && (
                                <div className="space-y-3">
                                    <p className="font-medium text-gray-700">Do you consume meat?</p>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => setProfile(p => ({ ...p, meat_allowed: true }))}
                                            className={`flex-1 p-3 rounded-lg border-2 transition-all ${profile.meat_allowed ? 'border-green-500 bg-green-50 text-green-700 font-bold' : 'border-slate-100'
                                                }`}
                                        >
                                            Yes
                                        </button>
                                        <button
                                            onClick={() => setProfile(p => ({ ...p, meat_allowed: false }))}
                                            className={`flex-1 p-3 rounded-lg border-2 transition-all ${!profile.meat_allowed ? 'border-red-500 bg-red-50 text-red-700 font-bold' : 'border-slate-100'
                                                }`}
                                        >
                                            No
                                        </button>
                                    </div>
                                </div>
                            )}

                            <div className="pt-4 flex justify-between">
                                <button onClick={() => setStep(1)} className="text-slate-500 hover:text-slate-800">Back</button>
                                <button
                                    onClick={() => setStep(3)}
                                    className="bg-blue-600 text-white px-6 py-2 rounded-full font-bold hover:bg-blue-700 flex items-center gap-2"
                                >
                                    Next <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 3: ALLERGIES */}
                    {step === 3 && (
                        <div className="space-y-4 animate-in slide-in-from-right-8 duration-300">
                            <h3 className="text-xl font-bold text-gray-800">Any food allergies?</h3>
                            <p className="text-gray-500 text-sm">We'll flag ingredients that contain these.</p>

                            <div className="grid grid-cols-2 gap-3 mt-4">
                                {["Milk", "Eggs", "Nuts", "Soy", "Wheat / Gluten", "Fish", "Shellfish", "Sesame"].map(alg => (
                                    <button
                                        key={alg}
                                        onClick={() => toggleAllergy(alg)}
                                        className={`p-3 rounded-lg border-2 text-left transition-all flex justify-between items-center ${profile.allergies?.includes(alg)
                                            ? 'border-red-500 bg-red-50 text-red-700 font-bold'
                                            : 'border-slate-100 hover:border-red-100 text-slate-700'
                                            }`}
                                    >
                                        {alg}
                                        {profile.allergies?.includes(alg) && <Check className="w-4 h-4" />}
                                    </button>
                                ))}
                            </div>

                            {/* Custom Allergy Input */}
                            <div className="mt-4">
                                <p className="text-sm font-medium text-slate-700 mb-2">Other allergies (comma separated):</p>
                                <input
                                    type="text"
                                    value={customAllergy}
                                    onChange={(e) => {
                                        setCustomAllergy(e.target.value)
                                        // We don't save to profile immediately, we parse on comma
                                    }}
                                    onBlur={() => {
                                        if (customAllergy.trim()) {
                                            const newAlgs = customAllergy.split(',').map(s => s.trim()).filter(Boolean)
                                            setProfile(prev => ({
                                                ...prev,
                                                allergies: [...prev.allergies, ...newAlgs]
                                            }))
                                            setCustomAllergy('') // Clear after adding
                                        }
                                    }}
                                    placeholder="e.g. Strawberries, Latex"
                                    className="w-full p-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                                />
                            </div>

                            <div className="pt-4 flex justify-between">
                                <button onClick={() => setStep(profile.diet === 'Vegan' ? 1 : 2)} className="text-slate-500 hover:text-slate-800">Back</button>
                                <button
                                    onClick={() => setStep(4)}
                                    className="bg-blue-600 text-white px-6 py-2 rounded-full font-bold hover:bg-blue-700 flex items-center gap-2"
                                >
                                    Review <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* STEP 4: CONFIRMATION */}
                    {step === 4 && (
                        <div className="space-y-6 animate-in slide-in-from-right-8 duration-300">
                            <div className="flex items-center justify-center mb-6">
                                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-green-600">
                                    <Check className="w-8 h-8" />
                                </div>
                            </div>

                            <h3 className="text-xl font-bold text-center text-gray-800">Profile Ready!</h3>

                            <div className="bg-slate-50 rounded-xl p-4 space-y-3">
                                <ProfileRow label="Diet" value={profile.diet} />
                                <ProfileRow label="Dairy" value={profile.dairy_allowed ? "Allowed" : "Not Allowed"} />
                                <ProfileRow label="Meat" value={profile.meat_allowed ? "Allowed" : "Not Allowed"} />
                                <ProfileRow label="Allergies" value={profile.allergies.length > 0 ? profile.allergies.join(", ") : "None"} />
                            </div>

                            <button
                                onClick={handleComplete}
                                className="w-full bg-blue-600 text-white py-4 rounded-xl font-bold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-600/20"
                            >
                                Save & Start Chatting
                            </button>
                            <button onClick={() => setStep(1)} className="w-full text-sm text-slate-500 hover:text-blue-600 flex items-center justify-center gap-1">
                                <Edit2 className="w-3 h-3" /> Edit Profile
                            </button>
                        </div>
                    )}

                </div>
            </div>
        </div>
    )
}

function ProfileRow({ label, value }: { label: string, value: string }) {
    return (
        <div className="flex justify-between items-center border-b border-slate-200 last:border-0 pb-2 last:pb-0">
            <span className="text-slate-500 font-medium">{label}</span>
            <span className="text-slate-800 font-bold">{value}</span>
        </div>
    )
}
