interface IconProps {
  className?: string;
  size?: number;
}

export function ChatIcon({ className, size = 24 }: IconProps) {
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
      {/* Recommended: Chat bubble or message icon from Multimedia Collection */}
      <path
        d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16Z"
        fill="currentColor"
      />
      <path
        d="M7 9H17V11H7V9ZM7 12H14V14H7V12Z"
        fill="currentColor"
      />
    </svg>
  );
}







