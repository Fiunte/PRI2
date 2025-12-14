"use client"

import { useEffect, useRef } from "react"
import { Search, X, Tag } from "lucide-react"
import type { ActiveFilter } from "@/lib/category-logic"

interface SearchBarProps {
  onSearch: (query: string) => void
  query: string
  activeFilters: ActiveFilter[]
  onRemoveFilter: (filter: ActiveFilter) => void
}

export default function SearchBar({ onSearch, query, activeFilters, onRemoveFilter }: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  return (
    <div className="w-full">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-primary/60" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search drugs by name, ingredient, or category..."
          value={query}
          onChange={(e) => onSearch(e.target.value)}
          className="w-full rounded-lg border border-border bg-input px-4 py-3 pl-12 text-foreground placeholder-muted-foreground transition-all duration-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 hover:border-primary/50"
        />
        {query && (
          <button
            onClick={() => onSearch("")}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-primary"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {activeFilters.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2 animate-in fade-in slide-in-from-top-2">
          {activeFilters.map((filter, idx) => (
            <span
              key={`${filter.field}-${filter.value}-${idx}`}
              className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary border border-primary/20 hover:bg-primary/15 transition-colors"
            >
              <Tag className="h-3 w-3" />
              {filter.displayValue}
              <button
                onClick={() => onRemoveFilter(filter)}
                className="ml-1 rounded-full p-0.5 hover:bg-primary/20 transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <p className="mt-3 text-xs text-muted-foreground">
        {query.length > 0 ? "Press Enter or wait for results..." : "Type to search • Cmd+K to focus"}
      </p>
    </div>
  )
}
