import type { AddressLabel } from '@/shared/types';

export const ADDRESS_LABEL_LABELS: Record<AddressLabel, string> = {
  HOME: 'Дом',
  DACHA: 'Дача',
  WORK: 'Работа',
  PARENTS: 'Родители',
  OTHER: 'Другое',
};

export const ADDRESS_LABEL_ICONS: Record<AddressLabel, string> = {
  HOME: '🏠',
  DACHA: '🏡',
  WORK: '🏢',
  PARENTS: '👨‍👩‍👧',
  OTHER: '📍',
};

export const MINSK_MIR_STREETS = [
  'Аэродромная',
  'Белградская',
  'Братская',
  'Брилевская',
  'Германовская',
  'Жореса Алфёрова',
  'Игоря Лученка',
  'Лейтенанта Кижеватова',
  'Леонида Левина',
  'Леонида Щемелёва',
  'Михаила Савицкого',
  'Николы Теслы',
  'Переулок Физкультурный',
  'Проспект Мира',
  'Южная магистраль',
];

export const SERVICE_AREA_NAME = 'Минск-Мир';
export const SERVICE_AREA_DISTRICT = 'Октябрьский';
