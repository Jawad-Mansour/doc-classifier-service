export default function Spinner({ size = 'md' }) {
  const sizeMap = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-10 w-10' }
  return (
    <div
      className={`animate-spin rounded-full border-[3px] border-indigo-200 border-t-indigo-600 ${sizeMap[size]}`}
    />
  )
}
