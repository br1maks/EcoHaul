import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
}

export const Card = ({ children, className = '', onClick, hover = false }: CardProps) => {
  const baseStyles = 'bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-green-100 p-5 transition-all duration-200';
  const hoverStyles = hover ? 'hover:shadow-xl hover:scale-[1.02] cursor-pointer hover:border-green-200' : '';
  const clickableStyles = onClick ? 'active:scale-95' : '';

  return (
    <div
      className={`${baseStyles} ${hoverStyles} ${clickableStyles} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
};
