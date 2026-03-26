import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge = ({ children, variant = 'primary', size = 'md', className = '' }: BadgeProps) => {
  const baseStyles = 'inline-flex items-center font-medium rounded-full';

  const variantStyles = {
    primary: 'bg-primary-50 text-primary-700',
    secondary: 'bg-gray-100 text-gray-700',
    success: 'bg-green-50 text-green-700',
    warning: 'bg-yellow-50 text-yellow-700',
    danger: 'bg-red-50 text-red-700',
    info: 'bg-blue-50 text-blue-700',
  };

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
  };

  const colorStyles = className || variantStyles[variant];

  return (
    <span className={`${baseStyles} ${colorStyles} ${sizeStyles[size]}`}>
      {children}
    </span>
  );
};
