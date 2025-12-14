"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"

interface ProgressiveTextProps {
  text: string
  maxChars?: number
}

export default function ProgressiveText({ text, maxChars = 300 }: ProgressiveTextProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!text) return null

  if (text.length <= maxChars) {
    return <div className="text-sm leading-relaxed text-muted-foreground whitespace-pre-line">{text}</div>
  }

  const displayText = isExpanded ? text : text.slice(0, maxChars).trim() + "..."

  return (
    <div className="space-y-2">
      <div
        className={`text-sm leading-relaxed text-muted-foreground whitespace-pre-line transition-all duration-300 ${
          isExpanded ? "opacity-100" : "opacity-90"
        }`}
      >
        {displayText}
      </div>

      <div className="flex pt-1">
        <button
          onClick={(e) => {
            e.stopPropagation()
            setIsExpanded(!isExpanded)
          }}
          className="
            inline-flex items-center gap-1.5
            text-xs font-medium text-primary/80 hover:text-primary
            hover:underline underline-offset-4
            transition-colors duration-200
          "
        >
          {isExpanded ? (
            <>
              Show Less <ChevronUp className="w-3 h-3" />
            </>
          ) : (
            <>
              Show More <ChevronDown className="w-3 h-3" />
            </>
          )}
        </button>
      </div>
    </div>
  )
}
