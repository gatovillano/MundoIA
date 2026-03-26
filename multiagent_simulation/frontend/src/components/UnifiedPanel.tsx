"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

interface UnifiedPanelProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    icon: any;
    children: React.ReactNode;
    color?: string;
}

export default function UnifiedPanel({
    isOpen,
    onClose,
    title,
    subtitle,
    icon: Icon,
    children,
    color = "text-[#7c4dff]"
}: UnifiedPanelProps) {
    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ x: 400, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 400, opacity: 0 }}
                    transition={{ type: "spring", damping: 30, stiffness: 300 }}
                    className="fixed right-6 top-6 bottom-6 w-[400px] solid-panel rounded-2xl z-[70] flex flex-col overflow-hidden shadow-2xl border border-white/5"
                >
                    {/* Header */}
                    <div className="relative p-6 pb-6 border-b border-white/5 bg-gradient-to-b from-white/5 to-transparent">
                        <button
                            onClick={onClose}
                            className="absolute top-4 right-4 p-2 hover:bg-white/10 rounded-full transition-colors text-white/30 hover:text-white"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-2xl bg-white/5 border border-white/10 ${color}`}>
                                <Icon className="w-6 h-6" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-white tracking-widest uppercase font-mono leading-none mb-1.5">
                                    {title}
                                </h2>
                                {subtitle && (
                                    <div className={`text-[10px] uppercase tracking-[0.2em] font-bold opacity-70 ${color}`}>
                                        {subtitle}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                        {children}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
