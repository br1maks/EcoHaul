export type AddressLabel = 'HOME' | 'DACHA' | 'WORK' | 'PARENTS' | 'OTHER';

export interface Address {
  id: string;
  user_id: string;
  latitude: number;
  longitude: number;
  full_address: string;
  city: string;
  district: string;
  street: string;
  house_number: string;
  apartment?: string;
  entrance?: number;
  floor?: number;
  label?: AddressLabel;
  is_default: boolean;
  notes?: string;
  short_address: string;
  full_address_with_details: string;
  created_at: string;
}

export interface CreateAddressData {
  latitude: number;
  longitude: number;
  full_address: string;
  city: string;
  district: string;
  street: string;
  house_number: string;
  apartment?: string;
  entrance?: number;
  floor?: number;
  label?: AddressLabel;
  is_default?: boolean;
  notes?: string;
}

export interface UpdateAddressData {
  latitude?: number;
  longitude?: number;
  full_address?: string;
  city?: string;
  district?: string;
  street?: string;
  house_number?: string;
  apartment?: string;
  entrance?: number;
  floor?: number;
  label?: AddressLabel;
  is_default?: boolean;
  notes?: string;
}
