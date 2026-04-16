"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Globe, TrendingUp, Users, MessageCircle, Heart, Share2, Award, Crown, Star, MessageSquare, UserPlus, UserMinus, ArrowBigUp, ArrowBigDown, LayoutList } from "lucide-react";
import useGameStore from "@/store/useGameStore";
import { getHttpUrl } from "@/utils/apiConfig";

export default function SocialPanel() {
    const { agents, socialFeed, userId, socialMode, gruposDinamicos, selectAgent } = useGameStore();
    const [activeTab, setActiveTab] = useState<"feed" | "perfil" | "ranking" | "trending">("feed");

    const getApiHost = React.useCallback(() => {
        return getHttpUrl("");
    }, []);

    // Obtener métricas sociales de los agentes
    const agentsWithMetrics = agents
        .map(a => ({
            id: a.id,
            nombre: a.id,
            capital_social: a.social_metrics?.capital_social || 10,
            nivel_influencia: a.social_metrics?.nivel_influencia || "Desconocido",
            seguidores: a.social_metrics?.seguidores || 0,
            siguiendo: a.social_metrics?.siguiendo || 0,
            posts: a.social_metrics?.posts_publicados || 0,
            likes: a.social_metrics?.likes_recibidos || 0,
            debates_ganados: a.social_metrics?.debates_ganados || 0,
            profesion: a.profesion || "Ciudadano",
            grupo_id: a.grupo_id,
            color: a.color,
        }))
        .sort((a, b) => b.capital_social - a.capital_social);

    const topAgentes = agentsWithMetrics.slice(0, 5);
    const totalSeguidores = agentsWithMetrics.reduce((sum, a) => sum + a.seguidores, 0);
    const totalPosts = agentsWithMetrics.reduce((sum, a) => sum + a.posts, 0);

    return (
        <div className="flex flex-col h-full space-y-4">
            {/* Header Stats */}
            <div className="flex items-center justify-between px-1">
                <div className="text-[10px] font-bold text-[#00e5ff] uppercase tracking-widest flex items-center gap-2">
                    <Globe className="w-3 h-3" />
                    Red Social
                </div>
                <div className="flex gap-2">
                    <span className="text-[10px] bg-white/5 border border-white/5 px-2 py-0.5 rounded-lg text-white font-mono">
                        {agents.length} Agentes
                    </span>
                    <span className="text-[10px] bg-[#00e5ff]/10 border border-[#00e5ff]/10 px-2 py-0.5 rounded-lg text-[#00e5ff] font-mono">
                        {totalSeguidores} Seguidores
                    </span>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 p-1 bg-white/5 rounded-lg">
                <TabButton active={activeTab === "feed"} onClick={() => setActiveTab("feed")} label="Feed" icon={MessageSquare} />
                <TabButton active={activeTab === "perfil"} onClick={() => setActiveTab("perfil")} label="Perfil" icon={Users} />
                <TabButton active={activeTab === "ranking"} onClick={() => setActiveTab("ranking")} label="Top" icon={Crown} />
                <TabButton active={activeTab === "trending"} onClick={() => setActiveTab("trending")} label="Trends" icon={TrendingUp} />
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar pr-1">
                {activeTab === "feed" && (
                    socialMode === 'reddit' 
                        ? <RedditFeedTab posts={socialFeed} userId={userId || ""} grupos={gruposDinamicos} getApiHost={getApiHost} />
                        : <FeedTab posts={socialFeed} userId={userId || ""} getApiHost={getApiHost} />
                )}
                {activeTab === "perfil" && <PerfilTab userId={userId || ""} posts={socialFeed} />}
                {activeTab === "ranking" && <RankingTab agentes={topAgentes} onSelectAgent={selectAgent} />}
                {activeTab === "trending" && <TrendingTab agentes={agentsWithMetrics} onSelectAgent={selectAgent} />}
            </div>
        </div>
    );
}

function TabButton({ active, onClick, label, icon: Icon }: { active: boolean; onClick: () => void; label: string; icon: any }) {
    return (
        <button
            onClick={onClick}
            className={`flex-1 py-1.5 px-2 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                active
                    ? 'bg-[#00e5ff]/20 text-[#00e5ff] border border-[#00e5ff]/30'
                    : 'text-gray-500 hover:text-gray-300'
            }`}
        >
            <Icon className="w-3 h-3" />
            {label}
        </button>
    );
}

function RankingTab({ agentes, onSelectAgent }: { agentes: any[], onSelectAgent: (id: string) => void }) {
    const getNivelColor = (nivel: string) => {
        switch (nivel) {
            case "Legendario": return "text-yellow-400";
            case "Respetado": return "text-[#00e676]";
            case "Notorio": return "text-[#00e5ff]";
            default: return "text-gray-500";
        }
    };

    const getNivelIcon = (nivel: string) => {
        switch (nivel) {
            case "Legendario": return <Crown className="w-3 h-3 text-yellow-400" />;
            case "Respetado": return <Star className="w-3 h-3 text-[#00e676]" />;
            case "Notorio": return <Award className="w-3 h-3 text-[#00e5ff]" />;
            default: return <Users className="w-3 h-3 text-gray-500" />;
        }
    };

    return (
        <div className="space-y-3">
            {/* Podium */}
            {agentes.length >= 3 && (
                <div className="flex justify-center items-end gap-2 pb-4 border-b border-white/10">
                    <div className="flex flex-col items-center">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 flex items-center justify-center text-xs font-bold">
                            {agentes[1].id.replace("A", "")}
                        </div>
                        <div className="mt-2 text-[10px] text-gray-400">{agentes[1].capital_social.toFixed(0)}</div>
                        <div className="w-8 h-6 bg-gray-500/30 rounded-t" />
                    </div>
                    <div className="flex flex-col items-center -mt-2">
                        <Crown className="w-4 h-4 text-yellow-400 mb-1" />
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400/30 to-yellow-600/30 flex items-center justify-center text-sm font-bold border border-yellow-400/50">
                            {agentes[0].id.replace("A", "")}
                        </div>
                        <div className="mt-2 text-[10px] text-yellow-400">{agentes[0].capital_social.toFixed(0)}</div>
                        <div className="w-10 h-10 bg-yellow-500/30 rounded-t" />
                    </div>
                    <div className="flex flex-col items-center">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-xs font-bold">
                            {agentes[2].id.replace("A", "")}
                        </div>
                        <div className="mt-2 text-[10px] text-gray-400">{agentes[2].capital_social.toFixed(0)}</div>
                        <div className="w-8 h-4 bg-orange-500/30 rounded-t" />
                    </div>
                </div>
            )}

            {/* Lista detallada */}
            <div className="space-y-2">
                {agentes.map((agente, index) => (
                    <div 
                        key={agente.id} 
                        onClick={() => onSelectAgent(agente.id)}
                        className="p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-[#00e5ff]/30 cursor-pointer transition-all group"
                    >
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-bold w-4 ${index < 3 ? 'text-yellow-400' : 'text-gray-500'}`}>
                                    #{index + 1}
                                </span>
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#7c4dff] to-[#00e676] flex items-center justify-center text-[10px] font-bold">
                                    {agente.id.replace("A", "")}
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-xs font-bold text-white group-hover:text-[#00e5ff] transition-colors">{agente.profesion}</span>
                                    <div className="flex items-center gap-1">
                                        {getNivelIcon(agente.nivel_influencia)}
                                        <span className={`text-[9px] ${getNivelColor(agente.nivel_influencia)}`}>
                                            {agente.nivel_influencia}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="text-right">
                                <span className="text-lg font-bold text-[#00e5ff]">{agente.capital_social.toFixed(0)}</span>
                                <span className="text-[9px] text-gray-500"> CS</span>
                            </div>
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-[9px]">
                            <div className="bg-white/[0.03] rounded p-1.5 text-center">
                                <UserPlus className="w-3 h-3 mx-auto text-[#00e676] mb-1" />
                                <span className="text-gray-400">Seguid.</span>
                                <div className="font-bold text-white">{agente.seguidores}</div>
                            </div>
                            <div className="bg-white/[0.03] rounded p-1.5 text-center">
                                <UserMinus className="w-3 h-3 mx-auto text-gray-400 mb-1" />
                                <span className="text-gray-400">Siguiendo</span>
                                <div className="font-bold text-white">{agente.siguiendo}</div>
                            </div>
                            <div className="bg-white/[0.03] rounded p-1.5 text-center">
                                <MessageSquare className="w-3 h-3 mx-auto text-[#ffa000] mb-1" />
                                <span className="text-gray-400">Posts</span>
                                <div className="font-bold text-white">{agente.posts}</div>
                            </div>
                            <div className="bg-white/[0.03] rounded p-1.5 text-center">
                                <Heart className="w-3 h-3 mx-auto text-[#ec4899] mb-1" />
                                <span className="text-gray-400">Likes</span>
                                <div className="font-bold text-white">{agente.likes}</div>
                            </div>
                         </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function PerfilTab({ userId, posts }: { userId: string, posts: any[] }) {
    const arquitectoPosts = posts.filter(p => p.autor_id === `arquitecto_${userId}`);
    const totalPosts = arquitectoPosts.length;
    const totalLikes = arquitectoPosts.reduce((sum, p) => sum + (p.likes || 0), 0);
    const totalComments = arquitectoPosts.reduce((sum, p) => sum + (p.comentarios || 0), 0);

    return (
        <div className="space-y-4">
            {/* Perfil Header */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-yellow-400/10 to-orange-500/10 border border-yellow-400/20">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-lg font-bold text-black">
                        A
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-yellow-400">Arquitecto</h3>
                        <p className="text-xs text-gray-400">Creador del Mundo</p>
                    </div>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                        <div className="text-lg font-bold text-white">{totalPosts}</div>
                        <div className="text-xs text-gray-500">Posts</div>
                    </div>
                    <div>
                        <div className="text-lg font-bold text-white">{totalLikes}</div>
                        <div className="text-xs text-gray-500">Likes</div>
                    </div>
                    <div>
                        <div className="text-lg font-bold text-white">{totalComments}</div>
                        <div className="text-xs text-gray-500">Comentarios</div>
                    </div>
                </div>
            </div>

            {/* Mis Posts */}
            <div>
                <h4 className="text-sm font-bold text-white mb-3">Mis Publicaciones</h4>
                {arquitectoPosts.length === 0 ? (
                    <div className="py-10 text-center border border-dashed border-white/10 rounded-2xl bg-white/[0.02]">
                        <MessageCircle className="w-8 h-8 text-white/10 mx-auto mb-3" />
                        <p className="text-xs text-gray-500">Aún no has publicado nada</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {arquitectoPosts.map((post: any) => (
                            <div key={post.id} className="p-3 rounded-lg bg-white/5 border border-white/10">
                                <p className="text-sm text-gray-200 mb-2">{post.contenido}</p>
                                <div className="flex justify-between items-center text-xs text-gray-500">
                                    <span>{post.tipo || "post"}</span>
                                    <div className="flex gap-3">
                                        <span>❤️ {post.likes || 0}</span>
                                        <span>💬 {post.comentarios || 0}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function RedditFeedTab({ posts, userId, grupos, getApiHost }: { posts: any[], userId: string, grupos: Record<string, any>, getApiHost: () => string }) {
    const [expandedPost, setExpandedPost] = useState<string | null>(null);
    const [newPostContent, setNewPostContent] = useState("");
    const [isPosting, setIsPosting] = useState(false);
    const [commentInputs, setCommentInputs] = useState<{[key: string]: string}>({});
    const [selectedSubreddit, setSelectedSubreddit] = useState<string | null>(null);
    const [isLiking, setIsLiking] = useState<{[key: string]: boolean}>({});
    const [isCommenting, setIsCommenting] = useState<{[key: string]: boolean}>({});

    // Usar los posts reales del backend (Ordenados por LIKES para Reddit)
    const postsReales = (posts && posts.length > 0 ? [...posts] : [])
        .sort((a, b) => {
            // Prioridad a los likes
            if ((b.likes || 0) !== (a.likes || 0)) {
                return (b.likes || 0) - (a.likes || 0);
            }
            // Si tienen mismos likes, el más reciente primero
            return (b.timestamp || 0) - (a.timestamp || 0);
        });
    
    // Filtrar por subreddit si hay uno seleccionado
    const filteredPosts = selectedSubreddit 
        ? postsReales.filter(p => p.temas?.includes(selectedSubreddit) || p.tipo === selectedSubreddit || p.autor_id === selectedSubreddit)
        : postsReales;

    const subreddits = Array.from(new Set(postsReales.flatMap(p => p.temas || [])));
    const dynamicGroups = Object.values(grupos).map(g => g.nombre || g.id);

    const handlePost = async () => {
        if (!newPostContent.trim() || !userId) return;
        setIsPosting(true);
        try {
            const response = await fetch(`${getApiHost()}/social/post/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newPostContent.trim() })
            });
            if (response.ok) {
                setNewPostContent("");
            }
        } catch (error) {
            console.error('Error posting:', error);
        } finally {
            setIsPosting(false);
        }
    };

    const handleLike = async (postId: string) => {
        if (isLiking[postId]) return;
        setIsLiking(prev => ({ ...prev, [postId]: true }));
        try {
            await fetch(`${getApiHost()}/social/like/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ post_id: postId })
            });
        } catch (error) {
            console.error('Error liking:', error);
        } finally {
            setIsLiking(prev => ({ ...prev, [postId]: false }));
        }
    };

    const handleComment = async (postId: string) => {
        const content = commentInputs[postId]?.trim();
        if (!content || isCommenting[postId]) return;
        setIsCommenting(prev => ({ ...prev, [postId]: true }));
        try {
            const response = await fetch(`${getApiHost()}/social/comment/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ post_id: postId, content })
            });
            if (response.ok) {
                setCommentInputs(prev => ({ ...prev, [postId]: "" }));
            }
        } catch (error) {
            console.error('Error commenting:', error);
        } finally {
            setIsCommenting(prev => ({ ...prev, [postId]: false }));
        }
    };

    const handleShare = (post: any) => {
        const text = `r/${(post.temas?.[0] || post.tipo || "all").toLowerCase().replace(/\s+/g, '_')} - "${post.contenido}"`;
        navigator.clipboard.writeText(text);
        alert("¡Enlace de Reddit copiado!");
    };

    const handleAward = (post: any) => {
        alert(`¡Has otorgado un Award de Platino a u/${post.autor_id}!`);
    };

    const handleDownvote = (post: any) => {
        alert("El sistema relacional actual no procesa downvotes negativos, pero has expresado tu descontento divino.");
    };

    return (
        <div className="space-y-4">
            {/* Subreddits Header */}
            <div className="flex gap-2 overflow-x-auto pb-2 custom-scrollbar no-scrollbar">
                <button 
                    onClick={() => setSelectedSubreddit(null)}
                    className={`px-3 py-1 rounded-full text-[10px] font-bold whitespace-nowrap transition-all ${!selectedSubreddit ? 'bg-[#ff4500] text-white shadow-[0_0_10px_rgba(255,69,0,0.3)]' : 'bg-white/5 text-gray-500 hover:bg-white/10'}`}
                >
                    r/all
                </button>
                {dynamicGroups.map(name => (
                    <button 
                        key={name}
                        onClick={() => setSelectedSubreddit(name)}
                        className={`px-3 py-1 rounded-full text-[10px] font-bold whitespace-nowrap transition-all ${selectedSubreddit === name ? 'bg-[#ff4500] text-white shadow-[0_0_10px_rgba(255,69,0,0.3)]' : 'bg-white/5 text-gray-500 hover:bg-white/10'}`}
                    >
                        r/{name.toLowerCase().replace(/\s+/g, '_')}
                    </button>
                ))}
            </div>

            {/* Create Post (Reddit Style) */}
            <div className="bg-[#1a1a1b] border border-[#343536] rounded p-2 flex gap-2 items-center">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-xs font-bold text-black">
                    A
                </div>
                <input 
                    type="text"
                    value={newPostContent}
                    onChange={(e) => setNewPostContent(e.target.value)}
                    placeholder="Create Post"
                    className="flex-1 bg-[#272729] border border-[#343536] rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-white/20"
                    onKeyDown={(e) => e.key === 'Enter' && handlePost()}
                />
                <button 
                    onClick={handlePost}
                    disabled={!newPostContent.trim() || isPosting}
                    className="p-1.5 text-gray-500 hover:text-white transition-colors disabled:opacity-30"
                >
                    {isPosting ? <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" /> : <Share2 className="w-4 h-4" />}
                </button>
            </div>

            {/* Posts List */}
            <div className="space-y-3">
                {filteredPosts.length === 0 ? (
                    <div className="py-20 text-center border border-[#343536] rounded bg-[#1a1a1b]">
                        <LayoutList className="w-12 h-12 text-[#343536] mx-auto mb-4" />
                        <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">
                            Wow, such empty
                        </p>
                    </div>
                ) : (
                    filteredPosts.map((post: any) => (
                        <div key={post.id} className="flex bg-[#1a1a1b] border border-[#343536] hover:border-[#818384] rounded overflow-hidden transition-colors">
                            {/* Vote Sidebar */}
                            <div className="w-10 bg-[#151516] flex flex-col items-center py-2 gap-1">
                                <button 
                                    onClick={() => handleLike(post.id)}
                                    disabled={isLiking[post.id]}
                                    className={`transition-colors ${post.likes_por?.includes(userId) ? 'text-[#ff4500]' : 'text-gray-500 hover:text-[#ff4500]'}`}
                                >
                                    <ArrowBigUp className={`w-6 h-6 ${post.likes_por?.includes(userId) ? 'fill-[#ff4500]' : ''} ${isLiking[post.id] ? 'animate-pulse' : ''}`} />
                                </button>
                                <span className={`text-[11px] font-bold ${post.likes_por?.includes(userId) ? 'text-[#ff4500]' : 'text-gray-300'}`}>
                                    {post.likes || 0}
                                </span>
                                <button onClick={() => handleDownvote(post)} className="text-gray-500 hover:text-[#7193ff] transition-colors">
                                    <ArrowBigDown className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Content Area */}
                            <div className="flex-1 p-2 flex flex-col">
                                <div className="flex items-center gap-1.5 text-[10px] mb-2">
                                    <div className="w-4 h-4 rounded-full bg-[#ff4500] flex items-center justify-center text-[8px] font-bold text-white">
                                        r/
                                    </div>
                                    <span className="font-bold text-white hover:underline cursor-pointer">
                                        r/{(post.temas?.[0] || post.tipo || "all").toLowerCase().replace(/\s+/g, '_')}
                                    </span>
                                    <span className="text-gray-500">• Posted by</span>
                                    <span className="text-gray-500 hover:underline cursor-pointer">
                                        u/{post.autor_id?.startsWith("arquitecto_") ? "architect" : post.autor_id}
                                    </span>
                                </div>

                                <h3 className="text-sm font-medium text-gray-100 mb-2 leading-snug">
                                    {post.contenido}
                                </h3>

                                {post.temas && post.temas.length > 1 && (
                                    <div className="flex gap-1 mb-3">
                                        {post.temas.slice(1).map((tema: string, i: number) => (
                                            <span key={i} className="text-[9px] px-1.5 py-0.5 rounded-full bg-white/5 text-gray-400">
                                                #{tema}
                                            </span>
                                        ))}
                                    </div>
                                )}

                                {/* Actions Bar */}
                                <div className="flex gap-4 mt-auto pt-1">
                                    <button 
                                        onClick={() => setExpandedPost(expandedPost === post.id ? null : post.id)}
                                        className={`flex items-center gap-1.5 hover:bg-white/5 px-1.5 py-1 rounded text-[11px] font-bold transition-colors ${expandedPost === post.id ? 'bg-white/5 text-white' : 'text-gray-500'}`}
                                    >
                                        <MessageSquare className="w-4 h-4" />
                                        {post.comentarios || 0} Comments
                                    </button>
                                    <button onClick={() => handleShare(post)} className="flex items-center gap-1.5 text-gray-500 hover:bg-white/5 px-1.5 py-1 rounded text-[11px] font-bold transition-colors">
                                        <Share2 className="w-4 h-4" />
                                        Share
                                    </button>
                                    <button onClick={() => handleAward(post)} className="flex items-center gap-1.5 text-gray-500 hover:bg-white/5 px-1.5 py-1 rounded text-[11px] font-bold transition-colors">
                                        <Award className="w-4 h-4" />
                                        Award
                                    </button>
                                </div>

                                {/* Reddit Style Comments Expansion */}
                                {expandedPost === post.id && (
                                    <div className="mt-4 pl-2 border-l-2 border-[#343536] space-y-4">
                                        {/* Comment Input */}
                                        <div className="ml-2">
                                            <textarea
                                                value={commentInputs[post.id] || ""}
                                                onChange={(e) => setCommentInputs(prev => ({ ...prev, [post.id]: e.target.value }))}
                                                placeholder="What are your thoughts?"
                                                className="w-full bg-[#1a1a1b] border border-[#343536] rounded p-2 text-xs text-gray-200 focus:outline-none focus:border-white/20 min-h-[80px] resize-none"
                                            />
                                            <div className="flex justify-end mt-1">
                                                <button 
                                                    onClick={() => handleComment(post.id)}
                                                    disabled={!commentInputs[post.id]?.trim() || isCommenting[post.id]}
                                                    className="bg-white text-black px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider hover:bg-gray-200 transition-all disabled:opacity-50"
                                                >
                                                    {isCommenting[post.id] ? "Posting..." : "Comment"}
                                                </button>
                                            </div>
                                        </div>

                                        {/* Comments List */}
                                        <div className="space-y-4">
                                            {post.comentarios_detalle && post.comentarios_detalle.length > 0 ? (
                                                post.comentarios_detalle.map((com: any) => (
                                                    <div key={com.id} className="ml-2 flex gap-2">
                                                        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-bold ${com.autor_id?.startsWith("arquitecto_") ? 'bg-yellow-400 text-black' : 'bg-white/10 text-white'}`}>
                                                            {com.autor_id?.substring(0, 2).toUpperCase()}
                                                        </div>
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-2 text-[10px] mb-1">
                                                                <span className={`font-bold ${com.autor_id?.startsWith("arquitecto_") ? 'text-yellow-400' : 'text-gray-300'}`}>
                                                                    u/{com.autor_id?.startsWith("arquitecto_") ? "architect" : com.autor_id}
                                                                </span>
                                                                <span className="text-gray-500">• 1h ago</span>
                                                            </div>
                                                            <p className="text-[11px] text-gray-200 leading-normal bg-white/[0.02] p-2 rounded-lg">
                                                                {com.contenido}
                                                            </p>
                                                            <div className="flex gap-3 mt-2 text-[10px] font-bold text-gray-500">
                                                                <button onClick={() => setExpandedPost(post.id)} className="hover:text-white transition-colors">Reply</button>
                                                                <button onClick={() => handleAward(post)} className="hover:text-white transition-colors">Give Award</button>
                                                                <button onClick={() => handleShare(post)} className="hover:text-white transition-colors">Share</button>
                                                            </div>                                                        </div>
                                                    </div>
                                                ))
                                            ) : (
                                                <p className="text-[10px] text-gray-600 italic ml-2">No comments yet. Be the first to share what you think!</p>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

function FeedTab({ posts, userId, getApiHost }: { posts: any[], userId: string, getApiHost: () => string }) {
    const [expandedPost, setExpandedPost] = useState<string | null>(null);
    const [newPostContent, setNewPostContent] = useState("");
    const [isPosting, setIsPosting] = useState(false);
    const [commentInputs, setCommentInputs] = useState<{[key: string]: string}>({});
    const [isLiking, setIsLiking] = useState<{[key: string]: boolean}>({});
    const [isCommenting, setIsCommenting] = useState<{[key: string]: boolean}>({});

    // Usar los posts reales del backend
    const postsReales = (posts && posts.length > 0 ? [...posts] : [])
        .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

    const handlePost = async () => {
        if (!newPostContent.trim() || !userId) return;

        setIsPosting(true);
        try {
            const response = await fetch(`${getApiHost()}/social/post/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newPostContent.trim() })
            });

            if (response.ok) {
                setNewPostContent("");
                // The post will appear in the feed via websocket updates
            } else {
                console.error('Error posting:', await response.text());
            }
        } catch (error) {
            console.error('Error posting:', error);
        } finally {
            setIsPosting(false);
        }
    };

    const handleLike = async (postId: string) => {
        setIsLiking(prev => ({ ...prev, [postId]: true }));
        try {
            const response = await fetch(`${getApiHost()}/social/like/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ post_id: postId })
            });

            if (!response.ok) {
                console.error('Error liking:', await response.text());
            }
            // Update will come via websocket
        } catch (error) {
            console.error('Error liking:', error);
        } finally {
            setIsLiking(prev => ({ ...prev, [postId]: false }));
        }
    };

    const handleComment = async (postId: string) => {
        const content = commentInputs[postId]?.trim();
        if (!content) return;

        setIsCommenting(prev => ({ ...prev, [postId]: true }));
        try {
            const response = await fetch(`${getApiHost()}/social/comment/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ post_id: postId, content })
            });

            if (response.ok) {
                setCommentInputs(prev => ({ ...prev, [postId]: "" }));
            } else {
                console.error('Error commenting:', await response.text());
            }
            // Update will come via websocket
        } catch (error) {
            console.error('Error commenting:', error);
        } finally {
            setIsCommenting(prev => ({ ...prev, [postId]: false }));
        }
    };

    const handleShare = (post: any) => {
        const text = `Mira este post de ${post.autor_id} en MundoIA: "${post.contenido}"`;
        navigator.clipboard.writeText(text);
        // Podríamos añadir un toast aquí si existiera
        alert("¡Enlace copiado al portapapeles!");
    };

    const handleAward = (post: any) => {
        alert(`Has otorgado un Premio Divino a ${post.autor_id}. ¡Su capital social ha aumentado!`);
        // Opcionalmente llamar a un god-mode action que suba el capital social
    };

    if (postsReales.length === 0) {
        return (
            <div className="py-20 text-center border border-dashed border-white/10 rounded-2xl bg-white/[0.02]">
                <MessageCircle className="w-12 h-12 text-white/10 mx-auto mb-4" />
                <p className="text-xs text-gray-500 font-mono tracking-wider uppercase">
                    No hay publicaciones aún...
                </p>
                <p className="text-[9px] text-gray-600 mt-2">
                    Los agentes crearán posts al interactuar socialmente
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {/* Arquitecto Post Input */}
            <div className="p-3 rounded-xl bg-gradient-to-r from-[#7c4dff]/10 to-[#00e676]/10 border border-[#7c4dff]/20">
                <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-[8px] font-bold text-black">
                        A
                    </div>
                    <span className="text-xs text-yellow-400 font-bold">Arquitecto</span>
                </div>
                <textarea
                    value={newPostContent}
                    onChange={(e) => setNewPostContent(e.target.value)}
                    placeholder="Comparte tus pensamientos con el mundo..."
                    className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-sm text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:border-[#7c4dff]/50"
                    rows={2}
                    maxLength={280}
                />
                <div className="flex justify-between items-center mt-2">
                    <span className="text-[10px] text-gray-500">{newPostContent.length}/280</span>
                    <button
                        onClick={handlePost}
                        disabled={!newPostContent.trim() || isPosting}
                        className="px-3 py-1 bg-[#7c4dff] hover:bg-[#7c4dff]/80 disabled:bg-gray-600 text-white text-xs font-bold rounded-lg transition-colors"
                    >
                        {isPosting ? "..." : "Publicar"}
                    </button>
                </div>
            </div>

            {postsReales.map((post: any) => (
                <div key={post.id} className="p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all">
                    <div className="flex items-center gap-2 mb-2">
                        {post.autor_id?.startsWith("arquitecto_") ? (
                            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-[8px] font-bold text-black">
                                A
                            </div>
                        ) : (
                            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#7c4dff] to-[#00e676] flex items-center justify-center text-[8px] font-bold">
                                {post.autor_id?.replace("A", "") || "?"}
                            </div>
                        )}
                        <span className={`text-xs ${post.autor_id?.startsWith("arquitecto_") ? 'text-yellow-400 font-bold' : 'text-gray-400'}`}>
                            {post.autor_id?.startsWith("arquitecto_") ? "Arquitecto" : post.autor_id}
                        </span>
                        <span className="text-[9px] text-gray-600">• {post.tipo || "post"}</span>
                    </div>
                    <p className="text-sm text-gray-200 mb-2">{post.contenido}</p>
                    {post.temas && post.temas.length > 0 && (
                        <div className="flex gap-1 mb-2 flex-wrap">
                            {post.temas.map((tema: string, i: number) => (
                                <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-[#7c4dff]/20 text-[#7c4dff]">
                                    {tema}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Likes con detalle de quiénes dieron like */}
                    <div className="flex gap-4 text-[10px] text-gray-500 mb-2">
                        <button
                            onClick={() => handleLike(post.id)}
                            disabled={isLiking[post.id]}
                            className="flex items-center gap-1 hover:text-[#ec4899] transition-colors disabled:opacity-50"
                        >
                            <Heart className={`w-3 h-3 ${isLiking[post.id] ? 'text-gray-500' : 'text-[#ec4899]'}`} />
                            {post.likes || 0}
                            {post.likes_por && post.likes_por.length > 0 && (
                                <span className="text-[8px] text-gray-600">
                                    ({post.likes_por.slice(0, 3).join(", ")}{post.likes_por.length > 3 ? "..." : ""})
                                </span>
                            )}
                        </button>
                        <button
                            onClick={() => setExpandedPost(expandedPost === post.id ? null : post.id)}
                            className={`flex items-center gap-1 hover:text-[#ffa000] transition-colors ${expandedPost === post.id ? 'text-[#ffa000]' : ''}`}
                        >
                            <MessageSquare className="w-3 h-3" /> {post.comentarios || 0}
                        </button>
                        <button onClick={() => handleShare(post)} className="flex items-center gap-1 hover:text-[#00e5ff] transition-colors">
                            <Share2 className="w-3 h-3" /> Compartir
                        </button>
                        <button onClick={() => handleAward(post)} className="flex items-center gap-1 hover:text-yellow-400 transition-colors">
                            <Award className="w-3 h-3" /> Premiar
                        </button>
                    </div>

                    {/* Panel expandido con comentarios y likes detallados */}
                    {expandedPost === post.id && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-2 pt-2 border-t border-white/10"
                        >
                            {/* Lista de likes */}
                            {post.likes_por && post.likes_por.length > 0 && (
                                <div className="mb-3">
                                    <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                                        <Heart className="w-2.5 h-2.5 text-[#ec4899]" /> Les gusta a:
                                    </div>
                                    <div className="flex flex-wrap gap-1">
                                        {post.likes_por.map((autorId: string, i: number) => (
                                            <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-[#ec4899]/10 text-[#ec4899]/80">
                                                {autorId}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Lista de comentarios */}
                            {post.comentarios_detalle && post.comentarios_detalle.length > 0 && (
                                <div>
                                    <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                                        <MessageSquare className="w-2.5 h-2.5 text-[#ffa000]" /> Comentarios:
                                    </div>
                                    <div className="space-y-2">
                                        {post.comentarios_detalle.map((comentario: any) => (
                                            <div key={comentario.id} className="bg-white/[0.03] rounded-lg p-2">
                                                <div className="flex items-center gap-1.5 mb-1">
                                                    {comentario.autor_id?.startsWith("arquitecto_") ? (
                                                        <div className="w-4 h-4 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-[6px] font-bold text-black">
                                                            A
                                                        </div>
                                                    ) : (
                                                        <div className="w-4 h-4 rounded-full bg-gradient-to-br from-[#ffa000]/50 to-[#ff6f00]/50 flex items-center justify-center text-[6px] font-bold">
                                                            {comentario.autor_id?.replace("A", "") || "?"}
                                                        </div>
                                                    )}
                                                    <span className={`text-[9px] font-medium ${comentario.autor_id?.startsWith("arquitecto_") ? 'text-yellow-400' : 'text-[#ffa000]'}`}>
                                                        {comentario.autor_id?.startsWith("arquitecto_") ? "Arquitecto" : comentario.autor_id}
                                                    </span>
                                                </div>
                                                <p className="text-[10px] text-gray-300 ml-5.5">{comentario.contenido}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Input para comentar */}
                            <div className="mt-3 pt-2 border-t border-white/5">
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={commentInputs[post.id] || ""}
                                        onChange={(e) => setCommentInputs(prev => ({ ...prev, [post.id]: e.target.value }))}
                                        placeholder="Escribe un comentario..."
                                        className="flex-1 bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-[#ffa000]/50"
                                        maxLength={140}
                                        onKeyPress={(e) => e.key === 'Enter' && handleComment(post.id)}
                                    />
                                    <button
                                        onClick={() => handleComment(post.id)}
                                        disabled={!commentInputs[post.id]?.trim() || isCommenting[post.id]}
                                        className="px-2 py-1 bg-[#ffa000] hover:bg-[#ffa000]/80 disabled:bg-gray-600 text-white text-xs font-bold rounded transition-colors"
                                    >
                                        {isCommenting[post.id] ? "..." : "💬"}
                                    </button>
                                </div>
                            </div>

                            {/* Si no hay likes ni comentarios */}
                            {(!post.likes_por || post.likes_por.length === 0) && (!post.comentarios_detalle || post.comentarios_detalle.length === 0) && (
                                <p className="text-[9px] text-gray-600 italic">Sin interacciones aún</p>
                            )}
                        </motion.div>
                    )}
                </div>
            ))}
        </div>
    );
}

function TrendingTab({ agentes, onSelectAgent }: { agentes: any[], onSelectAgent: (id: string) => void }) {
    // Calcular tendencias basadas en crecimiento de capital social
    const trending = agentes
        .map(a => ({
            ...a,
            crecimiento: a.posts * 2 + a.likes + a.debates_ganados * 5,
        }))
        .sort((a, b) => b.crecimiento - a.crecimiento)
        .slice(0, 5);

    return (
        <div className="space-y-3">
            <div className="text-[9px] text-gray-500 uppercase tracking-wider px-1">
                Agentes más activos
            </div>
            {trending.map((agente, index) => (
                <div 
                    key={agente.id} 
                    onClick={() => onSelectAgent(agente.id)}
                    className="flex items-center gap-3 p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-transparent hover:border-[#00e676]/30 cursor-pointer transition-all"
                >
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        index === 0 ? 'bg-[#ffa000]/20 text-[#ffa000]' : 'bg-white/10 text-gray-400'
                    }`}>
                        {index + 1}
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-white group-hover:text-[#00e676] transition-colors">{agente.id}</span>
                            <span className="text-[10px] text-[#00e5ff]">+{agente.crecimiento} pts</span>
                        </div>
                        <div className="flex gap-2 text-[9px] text-gray-500">
                            <span>{agente.posts} posts</span>
                            <span>{agente.likes} likes</span>
                            <span>{agente.debates_ganados} debates</span>
                        </div>
                    </div>
                    <TrendingUp className="w-4 h-4 text-[#00e676]" />
                </div>
            ))}
        </div>
    );
}