"use client"

import { useState, useEffect } from "react"
import { ExternalLink, Pill, Layers, ChevronLeft, ArrowRight } from "lucide-react"
import type { DrugResult } from "@/app/page"

interface SearchResultsProps {
  results: DrugResult[]
  onSelectResult: (result: DrugResult) => void
}

export default function SearchResults({ results, onSelectResult }: SearchResultsProps) {
  // State to track if we are viewing a specific cluster
  const [activeCluster, setActiveCluster] = useState<DrugResult | null>(null)

  // Reset cluster view if the main search results change (new search)
  useEffect(() => {
    setActiveCluster(null)
  }, [results])

  // --- VIEW 1: DRILL DOWN (INSIDE A CLUSTER) ---
  if (activeCluster && activeCluster.variants) {
    return (
      <div className="animate-in fade-in slide-in-from-right-4 duration-300">
        <button 
            onClick={() => setActiveCluster(null)}
            className="mb-4 flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
        >
            <ChevronLeft className="h-4 w-4" />
            Back to all results
        </button>

        <div className="mb-6 rounded-lg border border-primary/20 bg-primary/5 p-4">
            <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
                <Layers className="h-5 w-5" />
                {activeCluster.generic_name} Variants
            </h3>
            <p className="text-sm text-muted-foreground">
                Showing {activeCluster.variants.length} results grouped by Ingredient (UNII).
            </p>
        </div>

        <div className="space-y-3">
            {activeCluster.variants.map((variant, index) => (
                <ResultCard 
                    key={variant.id} 
                    result={variant} 
                    index={index} 
                    onClick={() => onSelectResult(variant)} 
                />
            ))}
        </div>
      </div>
    )
  }

  // --- VIEW 2: MAIN LIST ---
  if (results.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">No results found. Try a different search term.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {results.map((result, index) => (
        <ResultCard 
            key={result.id} 
            result={result} 
            index={index}
            onClick={() => {
                if (result.is_cluster) {
                    setActiveCluster(result)
                } else {
                    onSelectResult(result)
                }
            }} 
        />
      ))}
    </div>
  )
}

// --- SUB-COMPONENT: Unified Card for Single Items & Clusters ---
function ResultCard({ result, index, onClick }: { result: DrugResult, index: number, onClick: () => void }) {
    const isCluster = !!result.is_cluster

    return (
        <div style={{ animation: `fadeIn 0.3s ease-out ${index * 50}ms both` }}>
          <button
            onClick={onClick}
            className={`group w-full text-left rounded-lg border bg-card p-5 transition-all duration-200 hover:shadow-md cursor-pointer relative overflow-hidden
                ${isCluster 
                    ? "border-primary/40 hover:border-primary hover:bg-primary/5" 
                    : "border-border hover:border-primary/50 hover:bg-gradient-to-r hover:from-card hover:to-primary/5"
                }
            `}
          >
            {isCluster && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary/40 group-hover:bg-primary transition-colors" />
            )}

            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                {/* --- HEADER (Brand/Generic) --- */}
                <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors text-lg flex items-center gap-2">
                  {isCluster ? (
                      <span className="flex items-center gap-2">
                          <Layers className="h-5 w-5 text-primary" />
                          {result.generic_name || "Ingredient Group"}
                      </span>
                  ) : (
                      result.brand_name || "Unknown Brand"
                  )}
                  {result.score !== undefined && (
                    <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary border border-primary/20">
                      {Math.round(result.score * 100)}%
                    </span>
                  )}
                </h3>

                <p className="mt-1.5 text-sm text-muted-foreground font-medium truncate">
                  {isCluster 
                    ? `Grouped by UNII: ${Array.isArray(result.unii) ? result.unii.join(", ") : result.unii}` 
                    : result.generic_name
                  }
                </p>
                
                {/* --- NEW: SEMANTIC SNIPPET --- */}
                {/* This explains WHY it matched "Pain" even if the title is "Advil" */}
                {result.match_snippet && (
                    <div className="mt-3 relative rounded-md bg-muted/50 p-3 text-sm italic text-muted-foreground border border-border/50">
                        <span className="absolute left-2 top-2 text-primary/20 font-serif text-3xl leading-none">"</span>
                        <p className="pl-4 relative z-10">
                            ...{result.match_snippet}...
                        </p>
                    </div>
                )}

                {/* --- METADATA --- */}
                <div className="mt-3 flex items-center gap-2">
                    {isCluster ? (
                        <div className="flex items-center gap-1.5 text-xs font-medium text-white bg-primary/80 rounded-md px-2.5 py-1.5 w-fit shadow-sm">
                            <Layers className="h-3.5 w-3.5" />
                            <span>{result.cluster_count} Variants found</span>
                        </div>
                    ) : (
                        result.manufacturer && (
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/40 rounded-md px-2.5 py-1.5 w-fit">
                                <Pill className="h-3.5 w-3.5 text-primary/60" />
                                <span className="truncate max-w-[200px]">{result.manufacturer}</span>
                            </div>
                        )
                    )}
                </div>
              </div>

              {isCluster ? (
                  <ArrowRight className="ml-3 mt-1 h-5 w-5 flex-shrink-0 text-primary transition-transform group-hover:translate-x-1" />
              ) : (
                  <ExternalLink className="ml-3 mt-1 h-5 w-5 flex-shrink-0 text-muted-foreground/50 group-hover:text-primary transition-colors" />
              )}
            </div>
          </button>
        </div>
    )
}