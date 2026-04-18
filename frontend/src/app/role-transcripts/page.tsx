'use client';

import Link from 'next/link';
import { FormEvent, useMemo, useState } from 'react';
import { Download, ExternalLink, FileJson, Loader2, RefreshCw, Search } from 'lucide-react';

import { api } from '@/lib/api';
import { RoleTranscriptDumpResponse } from '@/types';


function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function formatDuration(seconds: number) {
  if (!seconds) {
    return 'Unknown';
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function roleSlug(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

export default function RoleTranscriptPage() {
  const [roleQuery, setRoleQuery] = useState('web developer');
  const [result, setResult] = useState<RoleTranscriptDumpResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const currentSlug = useMemo(() => {
    if (result?.roleSlug) {
      return result.roleSlug;
    }
    return roleSlug(roleQuery);
  }, [result?.roleSlug, roleQuery]);

  const handleBuild = async (event?: FormEvent) => {
    event?.preventDefault();
    setIsBuilding(true);
    setError(null);

    try {
      const response = await api.buildRoleTranscriptDump({
        roleQuery,
        topChannels: 3,
        videosPerChannel: 3,
        minDurationMinutes: 20,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to build transcript dump.');
    } finally {
      setIsBuilding(false);
    }
  };

  const handleDownload = async () => {
    if (!currentSlug) {
      return;
    }

    setIsDownloading(true);
    setError(null);
    try {
      const { blob, filename } = await api.downloadRoleTranscriptDump(currentSlug);
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download transcript dump.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/5 backdrop-blur-xl bg-slate-900/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-ocean-400 mb-1">Separate MVP</p>
            <h1 className="text-2xl font-semibold">Role Transcript Dump Builder</h1>
          </div>
          <Link href="/" className="btn-secondary text-sm px-4 py-2">
            Back to Expert Search
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="max-w-3xl mb-8">
          <p className="text-gray-300 text-lg leading-7">
            Build one canonical transcript dump per role. Each search refreshes the same stored dump in Postgres,
            using the top 3 expert channels and the latest 3 long-form videos per channel.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[420px,1fr]">
          <section className="glass-card p-6 h-fit">
            <div className="flex items-center gap-3 mb-4">
              <Search className="w-5 h-5 text-ocean-400" />
              <h2 className="text-lg font-semibold">Build / Refresh</h2>
            </div>
            <form onSubmit={handleBuild} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Role or topic</label>
                <input
                  value={roleQuery}
                  onChange={(event) => setRoleQuery(event.target.value)}
                  className="input-field"
                  placeholder="web developer"
                />
                <p className="text-xs text-gray-500 mt-2">
                  The backend will internally search for AI-relevant expert channels for this role.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="rounded-xl border border-white/10 bg-slate-900/40 p-3">
                  <div className="text-gray-500 mb-1">Channels</div>
                  <div className="font-semibold">Top 3</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-900/40 p-3">
                  <div className="text-gray-500 mb-1">Videos</div>
                  <div className="font-semibold">Latest 3</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-900/40 p-3">
                  <div className="text-gray-500 mb-1">Minimum length</div>
                  <div className="font-semibold">20m</div>
                </div>
              </div>

              <div className="flex gap-3 flex-wrap">
                <button type="submit" className="btn-primary flex items-center gap-2" disabled={isBuilding}>
                  {isBuilding ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                  <span>{result ? 'Refresh Dump' : 'Build Dump'}</span>
                </button>
                <button
                  type="button"
                  className="btn-secondary flex items-center gap-2"
                  disabled={!currentSlug || isDownloading}
                  onClick={handleDownload}
                >
                  {isDownloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  <span>Download JSON</span>
                </button>
              </div>
            </form>

            {error && (
              <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}
          </section>

          <section className="space-y-6">
            {!result ? (
              <div className="glass-card p-8">
                <div className="flex items-center gap-3 mb-3">
                  <FileJson className="w-5 h-5 text-ocean-400" />
                  <h2 className="text-lg font-semibold">Stored Dump Preview</h2>
                </div>
                <p className="text-gray-400 leading-7">
                  Run a build for a role to create the canonical transcript dump. The result will be stored in Postgres
                  under the role slug and can be refreshed later without touching the existing expert-search flow.
                </p>
              </div>
            ) : (
              <>
                <div className="glass-card p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.16em] text-ocean-400 mb-1">Current stored dump</p>
                      <h2 className="text-2xl font-semibold">{result.roleQuery}</h2>
                      <p className="text-sm text-gray-400 mt-2">Search query used: {result.searchQueryUsed}</p>
                    </div>
                    <div className="text-right text-sm text-gray-400">
                      <div>Created: {formatDate(result.createdAt)}</div>
                      <div>Refreshed: {formatDate(result.refreshedAt)}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mt-5">
                    <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
                      <div className="text-xs text-gray-500 mb-1">Role slug</div>
                      <div className="font-semibold break-all">{result.roleSlug}</div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
                      <div className="text-xs text-gray-500 mb-1">Expert channels</div>
                      <div className="font-semibold">{result.channelCount}</div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
                      <div className="text-xs text-gray-500 mb-1">Fetched transcripts</div>
                      <div className="font-semibold">{result.transcriptCount}</div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
                      <div className="text-xs text-gray-500 mb-1">Selection rule</div>
                      <div className="font-semibold">Top {result.topChannels} × Latest {result.videosPerChannel}</div>
                    </div>
                  </div>
                </div>

                {result.expertChannels.map((channel) => (
                  <article key={channel.channelId} className="glass-card p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-xs uppercase tracking-[0.16em] text-gray-500 mb-1">Rank {channel.rank}</div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-xl font-semibold">{channel.channelName}</h3>
                          <a href={channel.channelUrl} target="_blank" rel="noopener noreferrer" className="text-ocean-400">
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </div>
                        <p className="text-sm text-gray-400 mt-2">{channel.topicMatchSummary || 'No summary available.'}</p>
                      </div>
                      <div className="text-right text-sm">
                        <div className="text-gray-500">Score</div>
                        <div className="font-semibold">{channel.overallScore.toFixed(3)}</div>
                        <div className="text-gray-500 mt-2">Transcripts</div>
                        <div className="font-semibold">{channel.transcriptsFound}/{channel.selectedVideoCount}</div>
                      </div>
                    </div>

                    <div className="mt-5 space-y-4">
                      {channel.videos.map((video) => (
                        <div key={video.videoId} className="rounded-xl border border-white/10 bg-slate-900/35 p-4">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <a
                                href={video.videoUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-white hover:text-ocean-300 transition-colors"
                              >
                                {video.title}
                              </a>
                              <div className="text-xs text-gray-500 mt-2">
                                {video.publishedAt ? formatDate(video.publishedAt) : 'Unknown publish date'} · {formatDuration(video.durationSeconds)}
                              </div>
                            </div>
                            <div className="text-right text-xs">
                              <div
                                className={`inline-flex rounded-full px-2 py-1 ${
                                  video.transcriptStatus === 'fetched'
                                    ? 'bg-emerald-500/15 text-emerald-300'
                                    : 'bg-red-500/15 text-red-300'
                                }`}
                              >
                                {video.transcriptStatus}
                              </div>
                              {video.fetchedFromCache && (
                                <div className="text-gray-500 mt-2">cache hit</div>
                              )}
                            </div>
                          </div>

                          {video.transcriptError && (
                            <p className="text-xs text-red-300 mt-3">{video.transcriptError}</p>
                          )}

                          {video.transcriptText && (
                            <details className="mt-3">
                              <summary className="cursor-pointer text-sm text-ocean-300">Preview transcript</summary>
                              <pre className="mt-3 whitespace-pre-wrap text-xs leading-6 text-gray-300 max-h-72 overflow-y-auto rounded-xl border border-white/10 bg-slate-950/70 p-4">
                                {video.transcriptText}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
