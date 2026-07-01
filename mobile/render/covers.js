/*
 * Download cover images on the React Native side and return them as base64
 * data: URIs. Passing inlined images into the WebView keeps the canvas
 * "same-origin", so toDataURL() works (cross-origin covers would taint it).
 */
import * as FileSystem from 'expo-file-system/legacy';

function mimeFor(url) {
  const ext = (url.split('?')[0].split('.').pop() || 'jpg').toLowerCase();
  if (ext === 'png') return 'image/png';
  if (ext === 'gif') return 'image/gif';
  if (ext === 'webp') return 'image/webp';
  return 'image/jpeg';
}

async function toDataUri(url) {
  if (!url) return null;
  try {
    const tmp = `${FileSystem.cacheDirectory}cv_${Math.random().toString(36).slice(2)}`;
    const dl = await FileSystem.downloadAsync(url, tmp);
    if (dl.status !== 200) return null;
    const b64 = await FileSystem.readAsStringAsync(dl.uri, { encoding: FileSystem.EncodingType.Base64 });
    await FileSystem.deleteAsync(dl.uri, { idempotent: true });
    return `data:${mimeFor(url)};base64,${b64}`;
  } catch {
    return null; // renderer falls back to a text placeholder
  }
}

// Replace .coverUrl on every item in the given lists with an inlined data URI.
export async function inlineCovers(lists) {
  const all = lists.flat().filter(Boolean);
  await Promise.all(all.map(async (item) => {
    item.coverUrl = await toDataUri(item.coverUrl);
  }));
}
