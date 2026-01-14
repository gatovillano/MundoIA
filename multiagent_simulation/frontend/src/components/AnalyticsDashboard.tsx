'use client';

import React, { useEffect, useState } from 'react';
import { useSimulationStore } from '../store/useSimulationStore';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';
import { TrendingUp, Users, Heart, AlertTriangle } from 'lucide-react';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

export default function AnalyticsDashboard() {
    const { metrics, currentStep } = useSimulationStore();
    const [history, setHistory] = useState<any[]>([]);

    useEffect(() => {
        setHistory(prev => [...prev, { step: currentStep, ...metrics }].slice(-20));
    }, [currentStep, metrics]);

    const chartData = {
        labels: history.map(h => h.step),
        datasets: [
            {
                label: 'Índice de Gini',
                data: history.map(h => h.gini),
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                fill: true,
                tension: 0.4,
            },
            {
                label: 'Felicidad Promedio',
                data: history.map(h => h.happiness / 10), // Normalizar a 0-1
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                fill: true,
                tension: 0.4,
            }
        ]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                mode: 'index' as const,
                intersect: false,
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                max: 1,
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#94a3b8' }
            },
            x: {
                grid: { display: false },
                ticks: { color: '#94a3b8' }
            }
        }
    };

    return (
        <div className="p-8 h-full overflow-y-auto custom-scrollbar">
            <div className="max-w-6xl mx-auto space-y-8">
                <header>
                    <h2 className="text-2xl font-bold mb-2">Panel de Analíticas</h2>
                    <p className="text-slate-400">Monitoreo en tiempo real de la salud social y económica.</p>
                </header>

                {/* Metrics Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <MetricCard
                        title="Índice de Gini"
                        value={metrics.gini.toFixed(3)}
                        icon={TrendingUp}
                        color="text-indigo-400"
                        desc="Desigualdad de recursos"
                    />
                    <MetricCard
                        title="Felicidad"
                        value={`${(metrics.happiness * 10).toFixed(0)}%`}
                        icon={Heart}
                        color="text-emerald-400"
                        desc="Satisfacción de necesidades"
                    />
                    <MetricCard
                        title="Conflictos"
                        value={metrics.conflict_rate}
                        icon={AlertTriangle}
                        color="text-rose-400"
                        desc="Eventos hostiles recientes"
                    />
                    <MetricCard
                        title="Paso Actual"
                        value={currentStep}
                        icon={Users}
                        color="text-amber-400"
                        desc="Progreso de la simulación"
                    />
                </div>

                {/* Main Chart */}
                <div className="glass p-6 h-96">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="font-semibold text-slate-300">Evolución Social</h3>
                        <div className="flex gap-4 text-xs">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-indigo-500" />
                                <span className="text-slate-400">Gini</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                                <span className="text-slate-400">Felicidad</span>
                            </div>
                        </div>
                    </div>
                    <div className="h-72">
                        <Line data={chartData} options={options} />
                    </div>
                </div>
            </div>
        </div>
    );
}

function MetricCard({ title, value, icon: Icon, color, desc }: any) {
    return (
        <div className="glass p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm font-medium">{title}</span>
                <div className={`p-2 rounded-lg bg-white/5 ${color}`}>
                    <Icon size={18} />
                </div>
            </div>
            <div>
                <div className="text-2xl font-bold font-mono">{value}</div>
                <p className="text-[10px] text-slate-500 mt-1 uppercase tracking-wider">{desc}</p>
            </div>
        </div>
    );
}
