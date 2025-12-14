export default function LoadingState() {
  return (
    <div className="mt-8 space-y-3">
      {/* Animated shimmer skeletons */}
      {[...Array(3)].map((_, i) => (
        <div key={i} className="space-y-2 animate-fade-in">
          <div className="animate-shimmer rounded-lg h-6 w-1/3" />
          <div className="animate-shimmer rounded-lg h-4 w-2/3" />
        </div>
      ))}
    </div>
  )
}
