import { useState, useEffect, useRef } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, Pressable, ScrollView, ActivityIndicator, TextInput, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as MediaLibrary from 'expo-media-library';
import * as FileSystem from 'expo-file-system/legacy';
import {
  PollsReview, PollsEdit, SinglePollReview, PollComplete,
  PicksSelector, CarouselReview, CaptionEditor,
  BookInputForm, ReviewDraftView, ReviewTextEditor,
} from './components';

const DEFAULT_API_BASE = 'http://192.168.0.28:8001';
const STORAGE_KEY = 'watchtower.apiBase';
const FETCH_TIMEOUT_MS = 15000;

const COMMANDS = [
  { id: 'run',     label: 'Weekly Comics',   subtitle: 'New Comic Book Day carousel' },
  { id: 'movies',  label: 'Monthly Movies',  subtitle: 'Movies carousel' },
  { id: 'tv',      label: 'Monthly TV',      subtitle: 'TV carousel' },
  { id: 'review',  label: 'Book Review',     subtitle: 'Review creator' },
  { id: 'poll',    label: 'Daily Poll',      subtitle: 'Story poll' },
  { id: 'ideate',  label: 'Weekly Plan',     subtitle: 'Content ideation' },
];

async function fetchWithTimeout(url, options = {}, timeoutMs = FETCH_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try { return await fetch(url, { ...options, signal: controller.signal }); }
  finally { clearTimeout(timer); }
}

function humanizeError(e) {
  const msg = (e && e.message) || String(e);
  if (msg.includes('aborted') || msg.includes('Aborted')) return 'Server did not respond. Is uvicorn running?';
  if (msg.includes('Network request failed')) return 'Cannot reach server. Check WiFi and the URL in Settings.';
  return msg;
}

async function saveImagesToPhotos(urls, apiBase) {
  const errors = [];
  try {
    const perm = await MediaLibrary.requestPermissionsAsync();
    if (perm.status !== 'granted') {
      Alert.alert('Permission needed', 'Allow Photos access in iPhone Settings > Expo Go > Photos.');
      return { saved: 0, errors: ['no permission'] };
    }
  } catch (e) {
    return { saved: 0, errors: [`permission error: ${e.message}`] };
  }

  let saved = 0;
  for (let i = 0; i < urls.length; i++) {
    const url = urls[i];
    if (!url) { errors.push(`#${i}: empty url`); continue; }
    const fullUrl = `${apiBase}${url}`;
    const ext = (url.split('.').pop() || 'jpg').split('?')[0];
    const localPath = `${FileSystem.cacheDirectory}slide_${Date.now()}_${i}.${ext}`;
    try {
      const dl = await FileSystem.downloadAsync(fullUrl, localPath);
      if (dl.status !== 200) {
        errors.push(`#${i}: HTTP ${dl.status} from ${fullUrl}`);
        continue;
      }
      await MediaLibrary.createAssetAsync(dl.uri);
      saved++;
    } catch (e) {
      errors.push(`#${i}: ${e.message}`);
    }
  }
  return { saved, errors };
}

export default function App() {
  const [screen, setScreen] = useState('cover');
  const [activeCommand, setActiveCommand] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [error, setError] = useState(null);
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [apiBaseDraft, setApiBaseDraft] = useState(DEFAULT_API_BASE);
  const [deciding, setDeciding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [subscreen, setSubscreen] = useState('main');  // 'main' | 'edit_polls' | 'edit_caption' | 'edit_review' | 'book_form'
  const [editDraft, setEditDraft] = useState([]);
  const pollTimer = useRef(null);

  useEffect(() => {
    (async () => {
      const saved = await AsyncStorage.getItem(STORAGE_KEY);
      if (saved) { setApiBase(saved); setApiBaseDraft(saved); }
    })();
    return () => { if (pollTimer.current) clearInterval(pollTimer.current); };
  }, []);

  const saveApiBase = async () => {
    const trimmed = apiBaseDraft.trim().replace(/\/$/, '');
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      Alert.alert('Invalid URL', 'Must start with http:// or https://');
      return;
    }
    await AsyncStorage.setItem(STORAGE_KEY, trimmed);
    setApiBase(trimmed);
    setApiBaseDraft(trimmed);
    Alert.alert('Saved', `Server set to ${trimmed}`);
  };

  const testConnection = async () => {
    try {
      const res = await fetchWithTimeout(`${apiBaseDraft.trim().replace(/\/$/, '')}/`, {}, 5000);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      Alert.alert('Connected', JSON.stringify(await res.json(), null, 2));
    } catch (e) {
      Alert.alert('Connection failed', humanizeError(e));
    }
  };

  const tapCommand = (cmd) => {
    if (cmd.id === 'review') {
      // Review needs the input form first
      setActiveCommand(cmd);
      setScreen('pipeline');
      setSubscreen('book_form');
      setPipeline(null);
      setError(null);
    } else {
      startPipeline(cmd, null);
    }
  };

  const startPipeline = async (cmd, initialPayload) => {
    setError(null);
    setPipeline(null);
    setActiveCommand(cmd);
    setScreen('pipeline');
    setSubscreen('main');
    try {
      const body = initialPayload ? JSON.stringify({ payload: initialPayload }) : null;
      const res = await fetchWithTimeout(`${apiBase}/pipelines/${cmd.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      pollPipeline(data.pipeline_id);
    } catch (e) {
      setError(humanizeError(e));
    }
  };

  const pollPipeline = (pipelineId) => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    const tick = async () => {
      try {
        const res = await fetchWithTimeout(`${apiBase}/pipelines/${pipelineId}`, {}, 8000);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();
        setPipeline(data);
        if (data.status === 'complete' || data.status === 'failed' || data.status === 'awaiting_decision') {
          clearInterval(pollTimer.current);
          pollTimer.current = null;
        }
      } catch (e) {
        setError(humanizeError(e));
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    };
    tick();
    pollTimer.current = setInterval(tick, 2000);
  };

  const decide = async (action, payload) => {
    if (!pipeline) return;
    setDeciding(true);
    try {
      const res = await fetchWithTimeout(`${apiBase}/pipelines/${pipeline.id}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload ? { action, payload } : { action }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Server returned ${res.status}`);
      }
      pollPipeline(pipeline.id);
      setSubscreen('main');
    } catch (e) {
      setError(humanizeError(e));
    } finally {
      setDeciding(false);
    }
  };

  const saveCarouselSlides = async () => {
    if (!pipeline?.current_artifact?.slides_urls?.length) return;
    setSaving(true);
    try {
      const { saved, errors } = await saveImagesToPhotos(pipeline.current_artifact.slides_urls, apiBase);
      if (saved > 0 && errors.length === 0) {
        Alert.alert('Saved', `${saved} slide(s) saved to Photos`);
      } else {
        Alert.alert(`Saved ${saved}, failed ${errors.length}`, errors.slice(0, 5).join('\n\n'));
      }
    } catch (e) {
      Alert.alert('Save failed', humanizeError(e));
    } finally {
      setSaving(false);
    }
  };

  const savePollSlide = async () => {
    const url = pipeline?.current_artifact?.slide_url;
    if (!url) return;
    setSaving(true);
    try {
      const { saved, errors } = await saveImagesToPhotos([url], apiBase);
      if (saved > 0 && errors.length === 0) {
        Alert.alert('Saved', 'Slide saved to Photos');
      } else {
        Alert.alert(`Saved ${saved}, failed ${errors.length}`, errors.join('\n\n'));
      }
    } catch (e) {
      Alert.alert('Save failed', humanizeError(e));
    } finally {
      setSaving(false);
    }
  };

  const goBack = () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    pollTimer.current = null;
    setScreen('cover');
    setActiveCommand(null);
    setPipeline(null);
    setError(null);
    setSubscreen('main');
  };

  // ── Settings ────────────────────────────────────────────────────────────────
  if (screen === 'settings') {
    return (
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.jobHeader}>
          <Pressable onPress={() => setScreen('cover')} style={styles.backBtn}>
            <Text style={styles.backText}>← Back</Text>
          </Pressable>
          <Text style={styles.jobTitle}>Settings</Text>
        </View>
        <Text style={styles.fieldLabel}>API Server URL</Text>
        <TextInput
          style={styles.input} value={apiBaseDraft} onChangeText={setApiBaseDraft}
          autoCapitalize="none" autoCorrect={false} keyboardType="url" placeholderTextColor="#555"
        />
        <Text style={styles.fieldHint}>Current: {apiBase}</Text>
        <View style={{ height: 16 }} />
        <Pressable style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]} onPress={testConnection}>
          <Text style={styles.buttonLabel}>Test Connection</Text>
        </Pressable>
        <Pressable style={({ pressed }) => [styles.primaryButton, pressed && styles.primaryButtonPressed]} onPress={saveApiBase}>
          <Text style={styles.primaryButtonLabel}>Save</Text>
        </Pressable>
      </View>
    );
  }

  // ── Cover ───────────────────────────────────────────────────────────────────
  if (screen === 'cover') {
    return (
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.coverHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>TheWatchTower</Text>
            <Text style={styles.subtitle}>Content Creator</Text>
          </View>
          <Pressable onPress={() => setScreen('settings')} hitSlop={12}>
            <Text style={styles.gearIcon}>⚙</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.buttonList}>
          {COMMANDS.map((cmd) => (
            <Pressable
              key={cmd.id}
              style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
              onPress={() => tapCommand(cmd)}
            >
              <Text style={styles.buttonLabel}>{cmd.label}</Text>
              <Text style={styles.buttonSubtitle}>{cmd.subtitle}</Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>
    );
  }

  // ── Pipeline ────────────────────────────────────────────────────────────────
  const status = pipeline?.status;
  const stage = pipeline?.stage;
  const artifact = pipeline?.current_artifact;
  const isRunning = status === 'running_stage' || (!status && !error && subscreen === 'main' && activeCommand?.id !== 'review');
  const isAwaiting = status === 'awaiting_decision';
  const isDone = status === 'complete';
  const isFailed = status === 'failed';

  // Book input form (review only — shown before pipeline starts)
  if (subscreen === 'book_form') {
    return (
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <StatusBar style="light" />
        <View style={styles.jobHeader}>
          <Pressable onPress={goBack} style={styles.backBtn}>
            <Text style={styles.backText}>← Back</Text>
          </Pressable>
          <Text style={styles.jobTitle}>{activeCommand?.label}</Text>
        </View>
        <ScrollView style={styles.contentBox} contentContainerStyle={styles.contentInner} keyboardShouldPersistTaps="handled">
          <BookInputForm
            onSubmit={(form) => startPipeline(activeCommand, form)}
            onCancel={goBack}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <StatusBar style="light" />
      <View style={styles.jobHeader}>
        <Pressable onPress={goBack} style={styles.backBtn}>
          <Text style={styles.backText}>← Back</Text>
        </Pressable>
        <Text style={styles.jobTitle}>{activeCommand?.label}</Text>
        <View style={styles.statusRow}>
          {isRunning && <ActivityIndicator color="#888" size="small" />}
          <Text style={[styles.statusText, isDone && styles.statusDone, isFailed && styles.statusFailed]}>
            {error ? 'error' : (status ? `${status}${stage ? ' · ' + stage : ''}` : 'starting...')}
          </Text>
        </View>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      <ScrollView style={styles.contentBox} contentContainerStyle={styles.contentInner} keyboardShouldPersistTaps="handled">
        {/* IDEATE — polls */}
        {isAwaiting && artifact?.type === 'polls_table' && subscreen === 'main' && (
          <PollsReview
            artifact={artifact}
            onAction={decide}
            onEdit={() => { setEditDraft(artifact.polls.map(p => ({ ...p }))); setSubscreen('edit_polls'); }}
            disabled={deciding}
          />
        )}
        {isAwaiting && artifact?.type === 'polls_table' && subscreen === 'edit_polls' && (
          <PollsEdit
            draft={editDraft}
            onChange={(i, field, value) => setEditDraft(prev => prev.map((p, ix) => ix === i ? { ...p, [field]: value } : p))}
            onSave={() => decide('edit', { polls: editDraft })}
            onCancel={() => setSubscreen('main')}
            disabled={deciding}
          />
        )}

        {/* POLL — single poll */}
        {isAwaiting && artifact?.type === 'single_poll' && (
          <SinglePollReview artifact={artifact} onAction={decide} disabled={deciding} />
        )}

        {/* RUN / MOVIES / TV — picks selector */}
        {isAwaiting && artifact?.type === 'picks_selector' && (
          <PicksSelector
            artifact={artifact}
            onApprove={(payload) => decide('approve', payload)}
            disabled={deciding}
          />
        )}

        {/* RUN / MOVIES / TV / REVIEW — carousel review */}
        {(isAwaiting || isDone) && artifact?.type === 'carousel_review' && subscreen === 'main' && (
          <CarouselReview
            artifact={artifact}
            apiBase={apiBase}
            onAction={decide}
            onEditCaption={() => setSubscreen('edit_caption')}
            onSaveAll={saveCarouselSlides}
            disabled={deciding}
            saving={saving}
            isComplete={isDone}
          />
        )}
        {isAwaiting && artifact?.type === 'carousel_review' && subscreen === 'edit_caption' && (
          <CaptionEditor
            initial={artifact.caption || ''}
            onSave={(text) => decide('edit', { caption: text })}
            onCancel={() => setSubscreen('main')}
            disabled={deciding}
          />
        )}

        {/* REVIEW — review draft */}
        {isAwaiting && artifact?.type === 'review_draft' && subscreen === 'main' && (
          <ReviewDraftView
            artifact={artifact}
            onAction={decide}
            onEdit={() => setSubscreen('edit_review')}
            disabled={deciding}
          />
        )}
        {isAwaiting && artifact?.type === 'review_draft' && subscreen === 'edit_review' && (
          <ReviewTextEditor
            initial={artifact.review_text || ''}
            onSave={(text) => decide('edit', { review_text: text })}
            onCancel={() => setSubscreen('main')}
            disabled={deciding}
          />
        )}

        {/* IDEATE — final summary */}
        {isDone && artifact?.type === 'summary' && (
          <View>
            <Text style={styles.sectionTitle}>Complete</Text>
            <Text style={styles.sectionMeta}>{artifact.slides?.length || 0} slides built</Text>
            <View style={{ height: 12 }} />
            <Text style={styles.fieldLabel}>Plan</Text>
            <Text style={styles.planText}>{artifact.plan_text}</Text>
            <View style={{ height: 14 }} />
            <Text style={styles.fieldLabel}>Saved</Text>
            <Text style={styles.pathText}>{artifact.plan_path}</Text>
            <Text style={styles.pathText}>{artifact.polls_path}</Text>
          </View>
        )}
        {isDone && artifact?.type === 'poll_complete' && (
          <PollComplete artifact={artifact} apiBase={apiBase} onSave={savePollSlide} saving={saving} />
        )}

        {isFailed && pipeline?.error && (
          <View>
            <Text style={styles.errorBlock}>{pipeline.error}</Text>
            <View style={{ height: 8 }} />
            {(pipeline.log || []).slice(-30).map((line, i) => (
              <Text key={i} style={styles.logLine}>{line}</Text>
            ))}
          </View>
        )}
        {isRunning && !artifact && <Text style={styles.logLine}>Waiting for server...</Text>}
        {isRunning && artifact && <Text style={styles.logLine}>Running next stage...</Text>}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a', paddingTop: 60, paddingHorizontal: 20 },
  coverHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 30 },
  title: { color: '#fff', fontSize: 32, fontWeight: '700', letterSpacing: 0.5 },
  subtitle: { color: '#888', fontSize: 16, marginTop: 4 },
  gearIcon: { color: '#888', fontSize: 28 },
  buttonList: { paddingBottom: 40, gap: 12 },
  button: { backgroundColor: '#1c1c1e', borderRadius: 14, padding: 18, borderWidth: 1, borderColor: '#2a2a2c' },
  buttonPressed: { backgroundColor: '#2a2a2c', borderColor: '#3a3a3c' },
  buttonLabel: { color: '#fff', fontSize: 18, fontWeight: '600' },
  buttonSubtitle: { color: '#888', fontSize: 13, marginTop: 2 },
  primaryButton: { backgroundColor: '#0a84ff', borderRadius: 14, padding: 16, marginTop: 12, alignItems: 'center' },
  primaryButtonPressed: { backgroundColor: '#0a6dd0' },
  primaryButtonLabel: { color: '#fff', fontSize: 17, fontWeight: '600' },
  fieldLabel: { color: '#888', fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, marginTop: 12 },
  fieldHint: { color: '#666', fontSize: 12, marginTop: 6 },
  input: { backgroundColor: '#1c1c1e', borderRadius: 10, padding: 14, color: '#fff', fontSize: 15, borderWidth: 1, borderColor: '#2a2a2c' },
  jobHeader: { marginBottom: 16 },
  backBtn: { paddingVertical: 8 },
  backText: { color: '#0a84ff', fontSize: 16 },
  jobTitle: { color: '#fff', fontSize: 24, fontWeight: '700', marginTop: 8 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  statusText: { color: '#888', fontSize: 14, textTransform: 'uppercase', letterSpacing: 0.5 },
  statusDone: { color: '#30d158' },
  statusFailed: { color: '#ff453a' },
  errorBox: { backgroundColor: '#3a1a1a', borderRadius: 10, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: '#5a2a2a' },
  errorText: { color: '#ff8a80', fontSize: 14 },
  contentBox: { flex: 1, marginBottom: 40 },
  contentInner: { paddingBottom: 30 },
  sectionTitle: { color: '#fff', fontSize: 20, fontWeight: '700', marginBottom: 4 },
  sectionMeta: { color: '#888', fontSize: 13 },
  planText: { color: '#c8c8c8', fontFamily: 'Menlo', fontSize: 11, lineHeight: 16 },
  pathText: { color: '#888', fontFamily: 'Menlo', fontSize: 11 },
  logLine: { color: '#c8c8c8', fontFamily: 'Menlo', fontSize: 12, lineHeight: 16 },
  errorBlock: { color: '#ff8a80', fontFamily: 'Menlo', fontSize: 11, lineHeight: 16 },
});








