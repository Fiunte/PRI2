// page.tsx

"use client"

import { useState, useEffect } from "react"
import SearchBar from "@/components/search-bar"
import SearchResults from "@/components/search-results"
import LoadingState from "@/components/loading-state"
import DetailModal from "@/components/detail-modal"
import { extractFilterFromQuery, ActiveFilter } from "@/lib/category-logic"

export interface DrugResult {
  id: string
  brand_name: string
  generic_name: string
  score: number
  manufacturer?: string
  product_type?: string
  route?: string[]
  therapeutic_category?: string[]
  product_ndc?: string[]
  drug_id?: string
  unii?: string[]
  indications_and_usage?: string
  dosage_and_administration?: string
  warnings?: string
  active_ingredients?: string
  inactive_ingredients?: string
  storage_and_handling?: string
  purpose?: string
  is_cluster?: boolean
  cluster_count?: number
  variants?: DrugResult[] // Recursive type for the nested items
  match_snippet?: string; // The semantic sentence found
  match_score?: number;   // How confident the model is
}

export default function Home() {
  const [query, setQuery] = useState("")
  const [filters, setFilters] = useState<ActiveFilter[]>([])
  const [ignoredFilters, setIgnoredFilters] = useState<string[]>([])

  const [results, setResults] = useState<DrugResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [selectedResult, setSelectedResult] = useState<DrugResult | null>(null)

  // 1. SMART INPUT HANDLER
  const handleSearchInput = (input: string) => {

    // A. PRUNE IGNORE LIST
    const activeIgnoredFilters = ignoredFilters.filter(ignoredAlias =>
      input.toLowerCase().includes(ignoredAlias.toLowerCase())
    )

    if (activeIgnoredFilters.length !== ignoredFilters.length) {
      setIgnoredFilters(activeIgnoredFilters)
    }

    // B. EXTRACT
    const { cleanQuery, foundFilter } = extractFilterFromQuery(input, activeIgnoredFilters)

    if (foundFilter) {
      setFilters(prev => {
        const exists = prev.some(f => f.field === foundFilter.field && f.value === foundFilter.value)
        return exists ? prev : [...prev, foundFilter]
      })
      // NOTE: This sets query to "" (empty), but because we added a filter,
      // the useEffect below will still trigger a search!
      setQuery(cleanQuery)
    } else {
      setQuery(input)
    }
  }

  // 2. REMOVE FILTER & RESTORE ALIAS
  const handleRemoveFilter = (filterToRemove: ActiveFilter) => {
    setFilters(prev => prev.filter(f => f !== filterToRemove))

    if (filterToRemove.matchedAlias) {
      setIgnoredFilters(prev => [...prev, filterToRemove.matchedAlias])

      setQuery(prevQuery => {
        const restoredText = filterToRemove.matchedAlias.toLowerCase()
        // CHANGED: Appended to the end instead of prepended to the start
        return prevQuery ? `${prevQuery} ${restoredText}` : restoredText
      })
    }
  }

  // 3. CLEAR ALL
  const handleClear = () => {
    setQuery("")
    setFilters([])
    setResults([])
    setHasSearched(false)
    setIgnoredFilters([])
  }

  // 4. FETCH EFFECT
  useEffect(() => {
    const timeoutId = setTimeout(async () => {

      // LOGIC: Only stop/reset if BOTH are empty.
      // If query is "" but filters has items, this block is SKIPPED and search proceeds.
      if (!query.trim() && filters.length === 0) {
        setResults([])
        setHasSearched(false)
        return
      }

      setIsLoading(true)
      setHasSearched(true)

      try {
        const params = new URLSearchParams()

        // Only append 'query' if it actually has text.
        // If it's empty, we send only 'fq' params.
        if (query.trim()) params.append("query", query)

        filters.forEach(f => {
          params.append("fq", `${f.field}:"${f.value}"`)
        })

        // Example URL when filtering only: http://localhost:8000/search?fq=route:"NASAL"
        const res = await fetch(`http://localhost:8000/search?${params.toString()}`)
        if (!res.ok) throw new Error("Failed to fetch")
        const data = await res.json()

        const mappedResults: DrugResult[] = data.map((doc: any) => ({
          ...doc,
          route: Array.isArray(doc.route) ? doc.route : doc.route ? [doc.route] : [],
          therapeutic_category: Array.isArray(doc.therapeutic_category) ? doc.therapeutic_category : [],
          product_ndc: Array.isArray(doc.product_ndc) ? doc.product_ndc : [],
        }))

        setResults(mappedResults)
      } catch (error) {
        console.error("Search error:", error)
        setResults([])
      } finally {
        setIsLoading(false)
      }
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [query, filters])

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="border-b border-border bg-card">
        <div className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
          <h1 className="text-center text-3xl font-light tracking-tight sm:text-4xl">Drug Discovery</h1>
          <p className="mt-2 text-center text-sm text-muted-foreground">PRI 2025</p>
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-4 py-8">
        <SearchBar
          onSearch={handleSearchInput}
          query={query}
          activeFilters={filters}
          onRemoveFilter={handleRemoveFilter}
        />

        {isLoading && <LoadingState />}

        {!isLoading && hasSearched && (
          <div className="mt-8 animate-fade-in">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-medium text-muted-foreground">
                {results.length} result{results.length !== 1 ? "s" : ""} found
              </h2>
              <button onClick={handleClear} className="text-xs text-muted-foreground hover:text-foreground">Clear</button>
            </div>

            <SearchResults
              results={results}
              onSelectResult={setSelectedResult}
            />
          </div>
        )}
      </div>

      {selectedResult && (
        <DetailModal
          result={selectedResult}
          onClose={() => setSelectedResult(null)}
          onSelectResult={setSelectedResult}
        />
      )}
    </main>
  )
}