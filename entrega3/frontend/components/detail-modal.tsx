"use client"

import type React from "react"

import { useEffect } from "react"
import { X, Pill, Activity, AlertTriangle, FileText, Info, Box, CircleHelp } from "lucide-react"
import ProgressiveText from "./progressive-text"
import type { DrugResult } from "@/app/page"

interface DetailModalProps {
  result: DrugResult
  onClose: () => void
}

export default function DetailModal({ result, onClose }: DetailModalProps) {
  useEffect(() => {
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = "unset"
    }
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onClose])

  return (
    <>
      <div
        className="fixed inset-0 bg-black/40 z-40 animate-in fade-in duration-200 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div className="bg-card border border-border rounded-xl shadow-2xl pointer-events-auto w-full max-w-2xl max-h-[85vh] flex flex-col animate-in zoom-in-95 duration-200">
          {/* --- HEADER with gradient background --- */}
          <div className="flex-shrink-0 border-b border-border px-6 py-5 flex items-start justify-between bg-gradient-to-r from-primary/5 to-accent/5">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center rounded-md bg-primary/20 px-2.5 py-1 text-xs font-semibold text-primary border border-primary/30">
                  {result.product_type || "Drug"}
                </span>
                {result.score && (
                  <span className="text-xs font-medium text-muted-foreground">
                    Relevance: {result.score.toFixed(2)}
                  </span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-foreground leading-tight">{result.brand_name}</h2>
              <p className="text-sm font-medium text-muted-foreground mt-1">{result.generic_name}</p>
            </div>
            <button onClick={onClose} className="p-2 rounded-full hover:bg-muted transition-colors">
              <X className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>

          {/* --- SCROLLABLE CONTENT --- */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoBox label="Manufacturer" value={result.manufacturer} icon={<FileText className="w-4 h-4" />} />
              <InfoBox label="Route" value={result.route?.join(", ")} icon={<Activity className="w-4 h-4" />} />
              <InfoBox label="Product NDC" value={result.product_ndc?.join(", ")} icon={<Info className="w-4 h-4" />} />
              <InfoBox label="UNII" value={result.unii?.join(", ")} icon={<Info className="w-4 h-4" />} />
            </div>

            {(result.active_ingredients || result.inactive_ingredients) && (
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground flex items-center gap-2">
                  <Pill className="w-4 h-4 text-primary" /> Ingredients
                </h3>
                <div className="bg-primary/5 rounded-lg p-4 space-y-3 text-sm border border-primary/10">
                  {result.active_ingredients && (
                    <div>
                      <span className="font-semibold text-foreground">Active: </span>
                      <span className="text-muted-foreground">{result.active_ingredients}</span>
                    </div>
                  )}
                  {result.inactive_ingredients && (
                    <div>
                      <span className="font-semibold text-foreground">Inactive: </span>
                      <span className="text-muted-foreground">{result.inactive_ingredients}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            <Section
              title="Purpose & Indications"
              content={result.purpose || result.indications_and_usage}
              icon={<CircleHelp className="w-4 h-4" />}
            />

            <Section
              title="Dosage & Administration"
              content={result.dosage_and_administration}
              icon={<Pill className="w-4 h-4" />}
            />

            {result.warnings && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-destructive flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Warnings
                </h3>
                <div className="p-4 rounded-lg border border-destructive/20 bg-destructive/5">
                  <ProgressiveText text={result.warnings} />
                </div>
              </div>
            )}

            <Section title="Storage" content={result.storage_and_handling} icon={<Box className="w-4 h-4" />} />
          </div>
        </div>
      </div>
    </>
  )
}

function InfoBox({ label, value, icon }: { label: string; value?: string; icon: React.ReactNode }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-border bg-muted/30 hover:bg-muted/50 transition-colors">
      <div className="mt-0.5 text-primary/60">{icon}</div>
      <div>
        <div className="text-xs font-semibold text-muted-foreground uppercase">{label}</div>
        <div className="text-sm text-foreground font-medium mt-1">{value}</div>
      </div>
    </div>
  )
}

function Section({ title, content, icon }: { title: string; content?: string; icon?: React.ReactNode }) {
  if (!content) return null
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground flex items-center gap-2">
        {icon && <span className="text-primary">{icon}</span>}
        {title}
      </h3>
      <ProgressiveText text={content} />
    </div>
  )
}
