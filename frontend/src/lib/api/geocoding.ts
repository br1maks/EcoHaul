export interface GeocodeResult { latitude: number; longitude: number; full_address: string; displayName: string }

/** Explicit user action; the address is sent to OpenStreetMap Nominatim. */
export async function geocodeAddress(street: string, house: string): Promise<GeocodeResult | null> {
  const query = new URLSearchParams({ q: `${street} ${house}, Минск, Беларусь`, format: 'json', limit: '1', countrycodes: 'by' });
  const response = await fetch(`https://nominatim.openstreetmap.org/search?${query}`);
  if (!response.ok) throw new Error('Не удалось проверить адрес');
  const results: { lat: string; lon: string; display_name: string }[] = await response.json();
  const result = results[0];
  return result ? { latitude: Number(result.lat), longitude: Number(result.lon), full_address: result.display_name, displayName: result.display_name } : null;
}
