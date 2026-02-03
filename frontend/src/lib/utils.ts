import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toString();
}

export function formatScore(score: number): string {
  return (score * 100).toFixed(0);
}

export function getScoreColor(score: number): string {
  if (score >= 0.8) return 'text-emerald-400';
  if (score >= 0.6) return 'text-ocean-400';
  if (score >= 0.4) return 'text-yellow-400';
  return 'text-red-400';
}

export function getScoreBgColor(score: number): string {
  if (score >= 0.8) return 'bg-emerald-500';
  if (score >= 0.6) return 'bg-ocean-500';
  if (score >= 0.4) return 'bg-yellow-500';
  return 'bg-red-500';
}

export function getGrowthIcon(trend: string): '📈' | '📉' | '➡️' {
  const lower = trend.toLowerCase();
  if (lower.includes('rapid') || lower.includes('strong') || lower.includes('steady')) {
    return '📈';
  }
  if (lower.includes('declining') || lower.includes('slowing')) {
    return '📉';
  }
  return '➡️';
}

export function getLinkIcon(url: string): string {
  const lower = url.toLowerCase();
  if (lower.includes('github')) return '🐙';
  if (lower.includes('twitter') || lower.includes('x.com')) return '🐦';
  if (lower.includes('linkedin')) return '💼';
  if (lower.includes('huggingface')) return '🤗';
  if (lower.includes('arxiv')) return '📄';
  if (lower.includes('kaggle')) return '📊';
  return '🔗';
}

export function getDomainFromUrl(url: string): string {
  try {
    const domain = new URL(url).hostname.replace('www.', '');
    return domain;
  } catch {
    return url;
  }
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

