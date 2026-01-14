interface IconProps {
  className?: string;
  size?: number;
}

export function BookIcon({ className, size = 24 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Placeholder icon - Replace with SVG code from Flaticon */}
      {/* Recommended: Book or document icon from Multimedia Collection */}
      <path
        d="M18 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V4C20 2.9 19.1 2 18 2ZM18 20H6V4H18V20Z"
        fill="currentColor"
      />
      <path
        d="M8 6H16V8H8V6ZM8 10H16V12H8V10ZM8 14H13V16H8V14Z"
        fill="currentColor"
      />
    </svg>
  );
}






