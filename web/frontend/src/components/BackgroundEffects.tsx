"use client";

import { useEffect, useRef } from "react";

export default function BackgroundEffects() {
    const blobRef = useRef<HTMLDivElement>(null);
    const animationRef = useRef<Animation | null>(null);

    useEffect(() => {
        const handleMouseMove = (e: PointerEvent) => {
            if (blobRef.current) {
                const x = e.clientX;
                const y = e.clientY;
                const offsetX = x - 400;
                const offsetY = y - 400;

                if (animationRef.current) {
                    animationRef.current.cancel();
                }

                animationRef.current = blobRef.current.animate({
                    transform: `translate3d(${offsetX}px, ${offsetY}px, 0)`
                }, { duration: 3000, fill: "forwards" });
            }
        };

        window.addEventListener("pointermove", handleMouseMove);
        return () => window.removeEventListener("pointermove", handleMouseMove);
    }, []);

    return (
        <div className="fixed inset-0 z-[-1] overflow-hidden pointer-events-none">
            {/* Grid Pattern */}
            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03]" />

            {/* Ambient Gradient Blob */}
            <div
                ref={blobRef}
                className="absolute left-0 top-0 w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[120px] will-change-transform"
                style={{ transform: "translate3d(-400px, -400px, 0)" }}
            />

            {/* Static Gradient Elements */}
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-500/5 rounded-full blur-[100px]" />
            <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-[100px]" />

            {/* Scanlines (Subtle) */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] z-[1000] bg-[length:100%_4px,6px_100%] pointer-events-none opacity-20" />
        </div>
    );
}
