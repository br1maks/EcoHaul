import type { Order } from '@/shared/types';
import { Card, Badge } from '@/shared/components';
import { MapPin, Calendar, Trash2, Clock } from 'lucide-react';
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  GARBAGE_TYPE_LABELS,
  GARBAGE_TYPE_ICONS,
  CURRENCY_SYMBOL
} from '@/constants';

interface OrderCardProps {
  order: Order;
  onClick?: () => void;
}

export const OrderCard = ({ order, onClick }: OrderCardProps) => {
  const statusColor = ORDER_STATUS_COLORS[order.status];
  const statusLabel = ORDER_STATUS_LABELS[order.status];
  const garbageLabel = GARBAGE_TYPE_LABELS[order.garbage_type];
  const garbageIcon = GARBAGE_TYPE_ICONS[order.garbage_type];

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getBagsWord = (count: number): string => {
    const lastDigit = count % 10;
    const lastTwoDigits = count % 100;

    if (lastTwoDigits >= 11 && lastTwoDigits <= 19) {
      return 'мешков';
    }
    if (lastDigit === 1) {
      return 'мешок';
    }
    if (lastDigit >= 2 && lastDigit <= 4) {
      return 'мешка';
    }
    return 'мешков';
  };

  return (
    <Card hover={!!onClick} onClick={onClick}>
      {}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900">
              Заказ #{order.id.slice(0, 8)}
            </h3>
            <Badge className={statusColor} size="sm">
              {statusLabel}
            </Badge>
          </div>
          {order.pickup_address && (
            <div className="flex items-center gap-1 text-sm text-gray-600">
              <MapPin className="w-4 h-4" />
              <span>{order.pickup_address.full_address}</span>
            </div>
          )}
        </div>
        <p className="text-lg font-semibold text-green-600">
          {order.final_price.toFixed(2)} {CURRENCY_SYMBOL}
        </p>
      </div>

      {}
      <div className="space-y-2">
        {}
        <div className="flex items-center gap-2 text-sm text-gray-700">
          <Trash2 className="w-4 h-4" />
          <span>
            {garbageIcon} {garbageLabel} • {order.number_of_bags} {getBagsWord(order.number_of_bags)}
          </span>
        </div>

        {}
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Calendar className="w-4 h-4" />
          <span>{formatDate(order.created_at)}</span>
        </div>

        {}
        {order.scheduled_time && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <Clock className="w-4 h-4" />
            <span>Запланировано: {formatDate(order.scheduled_time)}</span>
          </div>
        )}

        {}
        {order.discount_amount > 0 && (
          <div className="text-sm text-green-600">
            Скидка: -{order.discount_amount.toFixed(2)} {CURRENCY_SYMBOL}
          </div>
        )}
      </div>
    </Card>
  );
};
