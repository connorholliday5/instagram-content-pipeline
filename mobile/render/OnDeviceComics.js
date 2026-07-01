/*
 * Fully on-device "New Comic Book Day" carousel.
 *
 * Flow (no PC, no server):
 *   1. Fetch + rank this week's comics from ComicVine (comicvine.js).
 *   2. Download covers to base64 on the RN side (covers.js).
 *   3. Pick your favorites.
 *   4. Draw all slides in a hidden WebView canvas (ComicsRenderer).
 *   5. Save the finished slides to Photos.
 *
 * The ComicVine key is stored locally in AsyncStorage.
 */
import { useState, useEffect } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, TextInput, Alert, Image, StyleSheet } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as MediaLibrary from 'expo-media-library';
import * as FileSystem from 'expo-file-system/legacy';
import { fetchComicsWeek } from './comicvine';
import { inlineCovers } from './covers';
import ComicsRenderer from './ComicsRenderer';

const CV_KEY_STORAGE = 'watchtower.comicvineKey';
const SLIDE_ORDER = ['slide_01_cover', 'slide_02_top10', 'slide_03_picks', 'slide_04_collectors'];

export default function OnDeviceComics({ onBack }) {
  const [apiKey, setApiKey] = useState('');
  const [keyDraft, setKeyDraft] = useState('');
  const [phase, setPhase] = useState('idle'); // idle | fetching | picking | rendering | done | error
  const [error, setError] = useState(null);
  const [week, setWeek] = useState(null);          // { streetDate, top, collectors }
  const [selected, setSelected] = useState({});    // index -> bool
  const [renderData, setRenderData] = useState(null);
  const [slides, setSlides] = useState(null);      // { name: dataURL }
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      const k = await AsyncStorage.getItem(CV_KEY_STORAGE);
      if (k) { setApiKey(k); setKeyDraft(k); }
    })();
  }, []);

  const saveKey = async () => {
    const k = keyDraft.trim();
    if (!k) { Alert.alert('Enter a key', 'Paste your ComicVine API key first.'); return; }
    await AsyncStorage.setItem(CV_KEY_STORAGE, k);
    setApiKey(k);
    Alert.alert('Saved', 'ComicVine key stored on this device.');
  };

  const fetchWeek = async () => {
    setError(null); setPhase('fetching'); setSlides(null); setRenderData(null);
    try {
      const w = await fetchComicsWeek(apiKey, { limit: 10 });
      setWeek(w);
      // Default picks = top 3, like the usual workflow.
      const sel = {}; w.top.slice(0, 3).forEach((_, i) => { sel[i] = true; });
      setSelected(sel);
      setPhase('picking');
    } catch (e) {
      setError(String(e.message || e)); setPhase('error');
    }
  };

  const build = async () => {
    setPhase('rendering'); setError(null);
    try {
      const picks = week.top.filter((_, i) => selected[i]);
      // Clone so inlining base64 doesn't mutate the on-screen thumbnails' URLs.
      const data = {
        streetDate: week.streetDate,
        top: week.top.map((x) => ({ ...x })),
        picks: picks.map((x) => ({ ...x })),
        collectors: (week.collectors || []).map((x) => ({ ...x })),
      };
      await inlineCovers([data.top, data.picks, data.collectors]);
      setRenderData(data);
    } catch (e) {
      setError(String(e.message || e)); setPhase('error');
    }
  };

  const onSlides = (s) => { setSlides(s); setPhase('done'); };
  const onRenderError = (msg) => { setError('Renderer: ' + msg); setPhase('error'); };

  const saveAll = async () => {
    if (!slides) return;
    setSaving(true);
    try {
      const perm = await MediaLibrary.requestPermissionsAsync();
      if (perm.status !== 'granted') { Alert.alert('Permission needed', 'Allow Photos access to save slides.'); setSaving(false); return; }
      let n = 0;
      for (const name of SLIDE_ORDER) {
        const url = slides[name];
        if (!url) continue;
        const b64 = url.split(',')[1];
        const path = `${FileSystem.cacheDirectory}${name}_${Date.now()}.jpg`;
        await FileSystem.writeAsStringAsync(path, b64, { encoding: FileSystem.EncodingType.Base64 });
        await MediaLibrary.createAssetAsync(path);
        n++;
      }
      Alert.alert('Saved', `${n} slide(s) saved to Photos.`);
    } catch (e) {
      Alert.alert('Save failed', String(e.message || e));
    } finally {
      setSaving(false);
    }
  };

  const toggle = (i) => setSelected((p) => ({ ...p, [i]: !p[i] }));

  // ---- render ----
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable onPress={onBack} style={{ paddingVertical: 8 }}><Text style={styles.link}>← Back</Text></Pressable>
        <Text style={styles.title}>Comics · On-Device</Text>
        <Text style={styles.sub}>Built on your phone — no PC or server</Text>
      </View>

      {error && <View style={styles.errBox}><Text style={styles.errText}>{error}</Text></View>}

      <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
        {/* API key */}
        {!apiKey && (
          <View style={styles.card}>
            <Text style={styles.label}>ComicVine API key</Text>
            <Text style={styles.hint}>Free — get one at comicvine.gamespot.com/api. Stored only on this device.</Text>
            <TextInput style={styles.input} value={keyDraft} onChangeText={setKeyDraft}
              autoCapitalize="none" autoCorrect={false} placeholder="paste key" placeholderTextColor="#555" />
            <Pressable style={styles.btn} onPress={saveKey}><Text style={styles.btnText}>Save key</Text></Pressable>
          </View>
        )}

        {apiKey && (phase === 'idle' || phase === 'error') && (
          <Pressable style={styles.primary} onPress={fetchWeek}><Text style={styles.primaryText}>Fetch this week</Text></Pressable>
        )}

        {phase === 'fetching' && <Row><ActivityIndicator color="#888" /><Text style={styles.muted}>  Fetching & ranking from ComicVine…</Text></Row>}

        {/* Pick favorites */}
        {phase === 'picking' && week && (
          <View>
            <Text style={styles.label}>Pick your favorites ({week.streetDate})</Text>
            {week.top.map((it, i) => (
              <Pressable key={i} style={[styles.pick, selected[i] && styles.pickOn]} onPress={() => toggle(i)}>
                <Text style={styles.pickNum}>{i + 1}</Text>
                <Text style={styles.pickTitle} numberOfLines={1}>{it.title}</Text>
                <Text style={styles.check}>{selected[i] ? '✓' : ''}</Text>
              </Pressable>
            ))}
            <Pressable style={styles.primary} onPress={build}><Text style={styles.primaryText}>Build slides</Text></Pressable>
          </View>
        )}

        {phase === 'rendering' && <Row><ActivityIndicator color="#888" /><Text style={styles.muted}>  Drawing slides on-device…</Text></Row>}

        {/* Result */}
        {phase === 'done' && slides && (
          <View>
            <Text style={styles.label}>Done — {SLIDE_ORDER.filter((n) => slides[n]).length} slides</Text>
            {SLIDE_ORDER.filter((n) => slides[n]).map((n) => (
              <Image key={n} source={{ uri: slides[n] }} style={styles.preview} resizeMode="contain" />
            ))}
            <Pressable style={styles.primary} onPress={saveAll} disabled={saving}>
              <Text style={styles.primaryText}>{saving ? 'Saving…' : 'Save all to Photos'}</Text>
            </Pressable>
            <Pressable style={styles.btn} onPress={fetchWeek}><Text style={styles.btnText}>Re-fetch</Text></Pressable>
          </View>
        )}
      </ScrollView>

      {/* Hidden rendering engine */}
      {renderData && phase === 'rendering' && (
        <ComicsRenderer data={renderData} onSlides={onSlides} onError={onRenderError} />
      )}
    </View>
  );
}

function Row({ children }) { return <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 16 }}>{children}</View>; }

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a', paddingTop: 60, paddingHorizontal: 20 },
  header: { marginBottom: 12 },
  link: { color: '#0a84ff', fontSize: 16 },
  title: { color: '#fff', fontSize: 24, fontWeight: '700', marginTop: 8 },
  sub: { color: '#888', fontSize: 13, marginTop: 2 },
  card: { backgroundColor: '#1c1c1e', borderRadius: 14, padding: 16, borderWidth: 1, borderColor: '#2a2a2c', marginTop: 8 },
  label: { color: '#fff', fontSize: 16, fontWeight: '600', marginTop: 14, marginBottom: 8 },
  hint: { color: '#888', fontSize: 12, marginBottom: 10 },
  input: { backgroundColor: '#111', borderRadius: 10, padding: 14, color: '#fff', fontSize: 15, borderWidth: 1, borderColor: '#2a2a2c' },
  btn: { backgroundColor: '#1c1c1e', borderRadius: 12, padding: 14, marginTop: 10, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2c' },
  btnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  primary: { backgroundColor: '#0a84ff', borderRadius: 12, padding: 16, marginTop: 14, alignItems: 'center' },
  primaryText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  muted: { color: '#888', fontSize: 14 },
  errBox: { backgroundColor: '#3a1a1a', borderRadius: 10, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: '#5a2a2a' },
  errText: { color: '#ff8a80', fontSize: 14 },
  pick: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1c1c1e', borderRadius: 10, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: '#2a2a2c' },
  pickOn: { borderColor: '#0a84ff', backgroundColor: '#152436' },
  pickNum: { color: '#888', fontSize: 14, width: 26 },
  pickTitle: { color: '#fff', fontSize: 15, flex: 1 },
  check: { color: '#0a84ff', fontSize: 18, width: 24, textAlign: 'right' },
  preview: { width: '100%', aspectRatio: 1080 / 1350, borderRadius: 8, marginBottom: 10, backgroundColor: '#111' },
});
