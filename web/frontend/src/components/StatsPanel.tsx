'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import useGameStore from '@/store/useGameStore';
import { TrendingUp, Users, Shield, Swords, Network, Baby, Activity, X, BarChart3 } from 'lucide-react';

interface StatHistory {
    step: number;
    population: number;
    attacks: number;
    friendships: number;
    enemies: number;
    groups: number;
    institutions: number;
    avgHealth: number;
    avgEnergy: number;
}

interface StatsPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function StatsPanel({ isOpen, onClose }: StatsPanelProps) {
    const { agents, relationships, gruposDinamicos, instituciones, step } = useGameStore();
    const historyRef = useRef<StatHistory[]>([]);
    const lineChartRef = useRef<SVGSVGElement>(null);
    const barChartRef = useRef<SVGSVGElement>(null);
    const pieChartRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        if (!isOpen) return;

        const newStat: StatHistory = {
            step: step,
            population: agents.length,
            attacks: relationships.filter((r: any) => r.type === 'enemigo' || r.type === 'conflict').length,
            friendships: relationships.filter((r: any) => r.type === 'amigo' || r.type === 'alianza').length,
            enemies: relationships.filter((r: any) => r.type === 'enemigo').length,
            groups: Object.keys(gruposDinamicos || {}).length,
            institutions: Object.keys(instituciones || {}).length,
            avgHealth: agents.length > 0 ? agents.reduce((sum: number, a: any) => sum + (a.salud || a.health || 50), 0) / agents.length : 0,
            avgEnergy: agents.length > 0 ? agents.reduce((sum: number, a: any) => sum + (a.energia || a.energy || 50), 0) / agents.length : 0,
        };

        historyRef.current = [...historyRef.current, newStat].slice(-50);

        drawLineChart();
        drawBarChart();
        drawPieChart();
    }, [isOpen, step, agents, relationships, gruposDinamicos, instituciones]);

    function drawLineChart() {
        if (!lineChartRef.current || historyRef.current.length < 2) return;

        const svg = d3.select(lineChartRef.current);
        svg.selectAll('*').remove();

        const width = Math.min(300, window.innerWidth - 80);
        const height = 180;
        const margin = { top: 20, right: 30, bottom: 30, left: 40 };

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const metrics = [
            { key: 'population', label: 'Población', color: '#00e676' },
            { key: 'friendships', label: 'Amistades', color: '#7c4dff' },
            { key: 'enemies', label: 'Enemigos', color: '#ff1744' },
            { key: 'groups', label: 'Grupos', color: '#ffd600' },
        ];

        const x = d3.scaleLinear()
            .domain(d3.extent(historyRef.current, d => d.step) as [number, number])
            .range([0, width - margin.left - margin.right]);

        const y = d3.scaleLinear()
            .domain([0, d3.max(historyRef.current, d => Math.max(d.population, d.groups + 1)) || 10])
            .range([height - margin.top - margin.bottom, 0]);

        g.append('g')
            .attr('transform', `translate(0,${height - margin.top - margin.bottom})`)
            .call(d3.axisBottom(x).ticks(5))
            .attr('color', '#666')
            .selectAll('text')
            .attr('fill', '#888')
            .attr('font-size', '10px');

        g.append('g')
            .call(d3.axisLeft(y).ticks(5))
            .attr('color', '#666')
            .selectAll('text')
            .attr('fill', '#888')
            .attr('font-size', '10px');

        metrics.forEach(metric => {
            const line = d3.line<StatHistory>()
                .x(d => x(d.step))
                .y(d => y((d as any)[metric.key]))
                .curve(d3.curveMonotoneX);

            g.append('path')
                .datum(historyRef.current)
                .attr('fill', 'none')
                .attr('stroke', metric.color)
                .attr('stroke-width', 2)
                .attr('d', line);
        });
    };

    function drawBarChart() {
        if (!barChartRef.current || historyRef.current.length === 0) return;

        const svg = d3.select(barChartRef.current);
        svg.selectAll('*').remove();

        const width = Math.min(300, window.innerWidth - 80);
        const height = 150;
        const margin = { top: 20, right: 20, bottom: 30, left: 40 };

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const latest = historyRef.current[historyRef.current.length - 1];
        const data = [
            { label: 'Pob.', value: latest.population, color: '#00e676' },
            { label: 'Amig.', value: latest.friendships, color: '#7c4dff' },
            { label: 'Enem.', value: latest.enemies, color: '#ff1744' },
            { label: 'Grup.', value: latest.groups, color: '#ffd600' },
            { label: 'Inst.', value: latest.institutions, color: '#00e5ff' },
        ];

        const x = d3.scaleBand()
            .domain(data.map(d => d.label))
            .range([0, width - margin.left - margin.right])
            .padding(0.3);

        const y = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.value) || 10])
            .range([height - margin.top - margin.bottom, 0]);

        g.append('g')
            .attr('transform', `translate(0,${height - margin.top - margin.bottom})`)
            .call(d3.axisBottom(x))
            .attr('color', '#666')
            .selectAll('text')
            .attr('fill', '#888')
            .attr('font-size', '10px');

        g.selectAll('.bar')
            .data(data)
            .enter()
            .append('rect')
            .attr('class', 'bar')
            .attr('x', d => x(d.label) || 0)
            .attr('y', d => y(d.value))
            .attr('width', x.bandwidth())
            .attr('height', d => height - margin.top - margin.bottom - y(d.value))
            .attr('fill', d => d.color)
            .attr('rx', 3);
    };

    function drawPieChart() {
        if (!pieChartRef.current || !agents.length) return;

        const svg = d3.select(pieChartRef.current);
        svg.selectAll('*').remove();

        const width = Math.min(150, window.innerWidth / 3);
        const height = 150;
        const radius = Math.min(width, height) / 2 - 10;

        const g = svg.append('g').attr('transform', `translate(${width / 2},${height / 2})`);

        const groupCount = agents.filter((a: any) => a.grupo_id).length;
        const noGroup = agents.length - groupCount;
        const data = [
            { label: 'En grupo', value: groupCount, color: '#7c4dff' },
            { label: 'Sin grupo', value: noGroup, color: '#666' },
        ];

        const pie = d3.pie<{ label: string; value: number; color: string }>()
            .value(d => d.value)
            .sort(null);

        const arc = d3.arc<d3.PieArcDatum<{ label: string; value: number; color: string }>>()
            .innerRadius(radius * 0.5)
            .outerRadius(radius);

        g.selectAll('path')
            .data(pie(data))
            .enter()
            .append('path')
            .attr('d', arc)
            .attr('fill', d => d.data.color)
            .attr('stroke', '#030305')
            .attr('stroke-width', 2);

        g.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '-0.2em')
            .attr('fill', '#fff')
            .attr('font-size', '14px')
            .attr('font-weight', 'bold')
            .text(`${agents.length}`);

        g.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '1em')
            .attr('fill', '#888')
            .attr('font-size', '10px')
            .text('Agentes');
    };

    if (!isOpen) return null;

    const latest = historyRef.current[historyRef.current.length - 1] || {
        population: 0, attacks: 0, friendships: 0, enemies: 0,
        groups: 0, institutions: 0, avgHealth: 0, avgEnergy: 0
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-[#0a0b10] border border-white/10 rounded-2xl w-[95vw] sm:w-[800px] max-w-[95vw] max-h-[90vh] sm:max-h-[80vh] overflow-hidden flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-white/10">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Activity className="w-5 h-5 text-purple-400" />
                        Estadísticas del Mundo
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                        <X className="w-5 h-5 text-white/60" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="glass-card p-4 rounded-xl">
                            <div className="flex items-center gap-2 text-white/60 mb-2">
                                <Users className="w-4 h-4" />
                                <span className="text-xs uppercase">Población</span>
                            </div>
                            <div className="text-2xl font-bold text-green-400">{latest.population}</div>
                        </div>
                        <div className="glass-card p-4 rounded-xl">
                            <div className="flex items-center gap-2 text-white/60 mb-2">
                                <Swords className="w-4 h-4" />
                                <span className="text-xs uppercase">Ataques</span>
                            </div>
                            <div className="text-2xl font-bold text-red-400">{latest.attacks}</div>
                        </div>
                        <div className="glass-card p-4 rounded-xl">
                            <div className="flex items-center gap-2 text-white/60 mb-2">
                                <Network className="w-4 h-4" />
                                <span className="text-xs uppercase">Amistades</span>
                            </div>
                            <div className="text-2xl font-bold text-purple-400">{latest.friendships}</div>
                        </div>
                        <div className="glass-card p-4 rounded-xl">
                            <div className="flex items-center gap-2 text-white/60 mb-2">
                                <Shield className="w-4 h-4" />
                                <span className="text-xs uppercase">Grupos</span>
                            </div>
                            <div className="text-2xl font-bold text-yellow-400">{latest.groups}</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="glass-card p-4 rounded-xl">
                            <h3 className="text-sm font-bold text-white/80 mb-3 flex items-center gap-2">
                                <TrendingUp className="w-4 h-4 text-purple-400" />
                                Tendencias Históricas
                            </h3>
                            <svg ref={lineChartRef} width="300" height="180" className="mx-auto" />
                            <div className="flex justify-center gap-4 mt-2 text-xs">
                                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-400"></span> Población</span>
                                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-400"></span> Amistades</span>
                                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400"></span> Enemigos</span>
                                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-400"></span> Grupos</span>
                            </div>
                        </div>

                        <div className="glass-card p-4 rounded-xl">
                            <h3 className="text-sm font-bold text-white/80 mb-3 flex items-center gap-2">
                                <BarChart3 className="w-4 h-4 text-purple-400" />
                                Distribución Actual
                            </h3>
                            <svg ref={barChartRef} width="300" height="150" className="mx-auto" />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="glass-card p-4 rounded-xl">
                            <h3 className="text-sm font-bold text-white/80 mb-3">Pertenencia a Grupos</h3>
                            <svg ref={pieChartRef} width="150" height="150" className="mx-auto" />
                            <div className="flex justify-center gap-4 mt-2 text-xs">
                                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-400"></span> En grupo</span>
                                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-500"></span> Solo</span>
                            </div>
                        </div>

                        <div className="glass-card p-4 rounded-xl col-span-2">
                            <h3 className="text-sm font-bold text-white/80 mb-3">Estado de Agentes</h3>
                            <div className="space-y-3">
                                <div>
                                    <div className="flex justify-between text-xs text-white/60 mb-1">
                                        <span>Salud Promedio</span>
                                        <span>{latest.avgHealth.toFixed(1)}%</span>
                                    </div>
                                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                        <div className="h-full bg-green-400" style={{ width: `${Math.min(100, latest.avgHealth)}%` }} />
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-xs text-white/60 mb-1">
                                        <span>Energía Promedio</span>
                                        <span>{latest.avgEnergy.toFixed(1)}%</span>
                                    </div>
                                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                        <div className="h-full bg-yellow-400" style={{ width: `${Math.min(100, latest.avgEnergy)}%` }} />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4 mt-4">
                                    <div className="text-center">
                                        <div className="text-2xl font-bold text-cyan-400">{latest.institutions}</div>
                                        <div className="text-xs text-white/60">Instituciones</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-2xl font-bold text-red-400">{latest.enemies}</div>
                                        <div className="text-xs text-white/60">Relaciones Enemigas</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}