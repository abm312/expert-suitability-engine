'use client';

import { useState } from 'react';
import { Search, Sparkles } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string, keywords: string[]) => void;
  isLoading?: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [keywords, setKeywords] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    const keywordList = keywords
      .split(',')
      .map(k => k.trim())
      .filter(Boolean);
    
    onSearch(query.trim(), keywordList);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="relative group">
        {/* Glow effect */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-ocean-500 to-emerald-500 rounded-2xl blur opacity-30 group-hover:opacity-50 transition duration-300" />
        
        <div className="relative glass-card p-2">
          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-3 px-4">
              <Search className="w-5 h-5 text-ocean-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Describe the expert you're looking for..."
                className="flex-1 bg-transparent border-none outline-none text-white placeholder-gray-500 text-lg py-3"
              />
            </div>
            
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Sparkles className="w-5 h-5" />
              )}
              <span>Find Experts</span>
            </button>
          </div>
          
          {/* Keywords input */}
          <div className="mt-2 px-4 pb-2">
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="Optional: Add keywords (comma-separated)"
              className="w-full bg-slate-800/50 border border-white/5 rounded-lg px-3 py-2 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-ocean-500/30"
            />
          </div>
        </div>
      </div>
      
      {/* Quick suggestions */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        {['AI/ML Engineer', 'LLM Expert', 'Data Scientist', 'MLOps Specialist', 'Computer Vision'].map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => setQuery(suggestion)}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-ocean-400 bg-slate-800/50 hover:bg-slate-800 rounded-lg border border-white/5 hover:border-ocean-500/30 transition-all"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </form>
  );
}

