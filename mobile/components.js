import { useState } from 'react';
import { View, Text, Pressable, TextInput, Image, ScrollView, StyleSheet, Alert } from 'react-native';
import * as Clipboard from 'expo-clipboard';

// ── Polls Review (ideate) ─────────────────────────────────────────────────────
export function PollsReview({ artifact, onAction, onEdit, disabled }) {
  return (
    <View>
      <Text style={s.sectionTitle}>{artifact.polls.length} polls — review</Text>
      <Text style={s.sectionMeta}>{artifact.comics_note}</Text>
      <Text style={s.sectionMeta}>NCBD: {artifact.next_wed}</Text>
      <View style={{ height: 12 }} />
      {artifact.polls.map((p, i) => (
        <View key={i} style={s.card}>
          <Text style={s.cardDate}>{p.date}</Text>
          <Text style={s.cardTitle}>{p.question}</Text>
          <Text style={s.cardLine}>A: {p.option_a}</Text>
          <Text style={s.cardLine}>B: {p.option_b}</Text>
        </View>
      ))}
      <View style={{ height: 12 }} />
      <View style={s.row}>
        <ApproveBtn label="Approve" onPress={() => onAction('approve')} disabled={disabled} />
        <SecondaryBtn label="Regenerate" onPress={() => onAction('regenerate')} disabled={disabled} />
      </View>
      <View style={{ height: 10 }} />
      <TertiaryBtn label="Edit polls" onPress={onEdit} disabled={disabled} />
    </View>
  );
}

export function PollsEdit({ draft, onChange, onSave, onCancel, disabled }) {
  return (
    <View>
      <Text style={s.sectionTitle}>Edit polls</Text>
      <Text style={s.sectionMeta}>Tap any field to change.</Text>
      <View style={{ height: 12 }} />
      {draft.map((p, i) => (
        <View key={i} style={s.card}>
          <Text style={s.cardDate}>{p.date}</Text>
          <Text style={s.editLabel}>Question</Text>
          <TextInput style={s.editInput} value={p.question} onChangeText={(v) => onChange(i, 'question', v)} multiline />
          <Text style={s.editLabel}>Option A</Text>
          <TextInput style={s.editInput} value={p.option_a} onChangeText={(v) => onChange(i, 'option_a', v)} />
          <Text style={s.editLabel}>Option B</Text>
          <TextInput style={s.editInput} value={p.option_b} onChangeText={(v) => onChange(i, 'option_b', v)} />
        </View>
      ))}
      <View style={{ height: 12 }} />
      <View style={s.row}>
        <ApproveBtn label="Save & Build" onPress={onSave} disabled={disabled} />
        <SecondaryBtn label="Cancel" onPress={onCancel} disabled={disabled} />
      </View>
    </View>
  );
}

// ── Single Poll (poll) ────────────────────────────────────────────────────────
export function PollComplete({ artifact, apiBase, onSave, saving }) {
  return (
    <View>
      <Text style={s.sectionTitle}>Complete</Text>
      <Text style={s.sectionMeta}>Slide saved</Text>
      <View style={{ height: 12 }} />
      {artifact.slide_url ? (
        <Image
          source={{ uri: `${apiBase}${artifact.slide_url}` }}
          style={{ width: '100%', height: 540, backgroundColor: '#1c1c1e', borderRadius: 8 }}
          resizeMode="contain"
        />
      ) : null}
      <View style={{ height: 12 }} />
      <Pressable
        style={({ pressed }) => [s.tertiaryBtn, pressed && { opacity: 0.7 }, saving && { opacity: 0.4 }]}
        onPress={onSave}
        disabled={saving}
      >
        <Text style={s.tertiaryText}>{saving ? 'Saving...' : 'Save to Photos'}</Text>
      </Pressable>
      <View style={{ height: 12 }} />
      <Text style={s.editLabel}>Path</Text>
      <Text style={{ color: '#888', fontFamily: 'Menlo', fontSize: 11 }}>{artifact.slide_path}</Text>
    </View>
  );
}

export function SinglePollReview({ artifact, onAction, disabled }) {
  const p = artifact.poll;
  return (
    <View>
      <Text style={s.sectionTitle}>Daily Poll</Text>
      <Text style={s.sectionMeta}>Category: {p.category}</Text>
      <View style={{ height: 12 }} />
      <View style={s.card}>
        <Text style={s.cardTitle}>{p.question}</Text>
        <Text style={s.cardLine}>A: {p.option_a}</Text>
        <Text style={s.cardLine}>B: {p.option_b}</Text>
      </View>
      <View style={{ height: 12 }} />
      <View style={s.row}>
        <ApproveBtn label="Approve" onPress={() => onAction('approve')} disabled={disabled} />
        <SecondaryBtn label="Regenerate" onPress={() => onAction('regenerate')} disabled={disabled} />
      </View>
    </View>
  );
}

// ── Picks Selector (run, movies, tv) ──────────────────────────────────────────
export function PicksSelector({ artifact, onApprove, disabled }) {
  const [selected, setSelected] = useState({});
  const [manualText, setManualText] = useState('');

  const toggle = (idx) => setSelected(prev => ({ ...prev, [idx]: !prev[idx] }));

  const submit = () => {
    const picks = Object.keys(selected).filter(k => selected[k]).map(k => parseInt(k, 10));
    const picks_extra = manualText.split(',').map(s => s.trim()).filter(Boolean);
    onApprove({ picks, picks_extra });
  };

  return (
    <View>
      <Text style={s.sectionTitle}>Tap items to pick</Text>
      <Text style={s.sectionMeta}>{artifact.items.length} items — select any number</Text>
      <View style={{ height: 12 }} />
      {artifact.items.map((it) => {
        const isSelected = !!selected[it.index];
        return (
          <Pressable
            key={it.index}
            onPress={() => toggle(it.index)}
            style={[s.pickRow, isSelected && s.pickRowSelected]}
          >
            {it.image_url ? (
              <Image source={{ uri: it.image_url }} style={s.thumb} />
            ) : <View style={[s.thumb, { backgroundColor: '#222' }]} />}
            <View style={{ flex: 1 }}>
              <Text style={s.pickTitle}>{it.title}</Text>
              {it.subtitle ? <Text style={s.pickSub}>{it.subtitle}</Text> : null}
            </View>
            <View style={[s.checkbox, isSelected && s.checkboxOn]}>
              {isSelected && <Text style={s.checkmark}>✓</Text>}
            </View>
          </Pressable>
        );
      })}
      {artifact.bonus_items?.length ? (
        <View style={{ marginTop: 18 }}>
          <Text style={s.sectionMeta}>Also notable (not selectable)</Text>
          {artifact.bonus_items.map((b, i) => (
            <View key={i} style={s.bonusRow}>
              <Text style={s.cardLine}>• {b.title}</Text>
              {b.subtitle ? <Text style={s.pickSub}>  {b.subtitle}</Text> : null}
            </View>
          ))}
        </View>
      ) : null}
      {artifact.allow_manual ? (
        <View style={{ marginTop: 18 }}>
          <Text style={s.editLabel}>Manual entries (comma-separated)</Text>
          <TextInput
            style={s.editInput}
            value={manualText}
            onChangeText={setManualText}
            placeholder="e.g. X-Men #100, Batman Annual #5"
            placeholderTextColor="#555"
            autoCorrect={false}
          />
        </View>
      ) : null}
      <View style={{ height: 14 }} />
      <ApproveBtn label="Approve picks" onPress={submit} disabled={disabled} />
    </View>
  );
}

// ── Carousel Review (run, movies, tv, review) ─────────────────────────────────
export function CarouselReview({ artifact, apiBase, onAction, onEditCaption, onSaveAll, disabled, saving, isComplete }) {
  return (
    <View>
      <Text style={s.sectionTitle}>{isComplete ? 'Complete' : 'Review slides'}</Text>
      <Text style={s.sectionMeta}>{artifact.slides_urls?.length || 0} slides</Text>
      <View style={{ height: 12 }} />
      <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false} style={s.slidesScroll}>
        {(artifact.slides_urls || []).map((url, i) => (
          <Image
            key={i}
            source={{ uri: `${apiBase}${url}` }}
            style={s.slideImage}
            resizeMode="contain"
          />
        ))}
      </ScrollView>
      <View style={{ height: 10 }} />
      <Pressable
        style={({ pressed }) => [s.tertiaryBtn, pressed && { opacity: 0.7 }, (disabled || saving) && { opacity: 0.4 }]}
        onPress={onSaveAll}
        disabled={disabled || saving}
      >
        <Text style={s.tertiaryText}>{saving ? 'Saving...' : 'Save all slides to Photos'}</Text>
      </Pressable>
      <View style={{ height: 14 }} />
      <View style={s.captionHeader}>
        <Text style={s.editLabel}>Caption</Text>
        <View style={{ flexDirection: 'row', gap: 16 }}>
          <Pressable
            onPress={async () => {
              await Clipboard.setStringAsync(artifact.caption || "");
              Alert.alert("Copied", "Caption + hashtags copied");
            }}
            hitSlop={8}
          >
            <Text style={s.copyLink}>Copy all</Text>
          </Pressable>
          <Pressable
            onPress={async () => {
              const cap = artifact.caption || "";
              const i = cap.indexOf("#");
              const tags = i >= 0 ? cap.slice(i) : "";
              await Clipboard.setStringAsync(tags);
              Alert.alert(tags ? "Copied" : "No hashtags", tags ? "Hashtags copied" : "No hashtags found in caption");
            }}
            hitSlop={8}
          >
            <Text style={s.copyLink}>Copy tags</Text>
          </Pressable>
        </View>
      </View>
      <View style={s.captionBox}>
        <Text selectable style={s.captionText}>{artifact.caption}</Text>
      </View>
      {!isComplete && (
        <>
          <View style={{ height: 12 }} />
          <View style={s.row}>
            <ApproveBtn label="Approve" onPress={() => onAction('approve')} disabled={disabled} />
            <SecondaryBtn label="Regen caption" onPress={() => onAction('regenerate')} disabled={disabled} />
          </View>
          <View style={{ height: 10 }} />
          <TertiaryBtn label="Edit caption" onPress={onEditCaption} disabled={disabled} />
        </>
      )}
      {artifact.saved ? (
        <Text style={[s.sectionMeta, { marginTop: 12, color: '#30d158' }]}>✓ Saved to 2026 reading list</Text>
      ) : null}
    </View>
  );
}

export function CaptionEditor({ initial, onSave, onCancel, disabled }) {
  const [text, setText] = useState(initial);
  return (
    <View>
      <Text style={s.sectionTitle}>Edit caption</Text>
      <View style={{ height: 10 }} />
      <TextInput
        style={[s.editInput, { minHeight: 240, textAlignVertical: 'top' }]}
        value={text}
        onChangeText={setText}
        multiline
      />
      <View style={{ height: 12 }} />
      <View style={s.row}>
        <ApproveBtn label="Save caption" onPress={() => onSave(text)} disabled={disabled} />
        <SecondaryBtn label="Cancel" onPress={onCancel} disabled={disabled} />
      </View>
    </View>
  );
}

// ── Book Input Form (review — before pipeline starts) ─────────────────────────
const RATINGS = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5];

export function BookInputForm({ onSubmit, onCancel, disabled }) {
  const [form, setForm] = useState({
    title: '', author: '', rating: 4,
    bullet_notes: '', next_title: '', next_author: '',
  });
  const update = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  const canSubmit = form.title.trim() && form.author.trim() && form.bullet_notes.trim() && form.next_title.trim() && form.next_author.trim();

  return (
    <View>
      <Text style={s.sectionTitle}>New Book Review</Text>
      <Text style={s.sectionMeta}>Fill in once, then we generate.</Text>
      <View style={{ height: 14 }} />
      <Text style={s.editLabel}>Book title</Text>
      <TextInput style={s.editInput} value={form.title} onChangeText={(v) => update('title', v)} placeholderTextColor="#555" />
      <Text style={s.editLabel}>Author</Text>
      <TextInput style={s.editInput} value={form.author} onChangeText={(v) => update('author', v)} placeholderTextColor="#555" />
      <Text style={s.editLabel}>Rating</Text>
      <View style={s.ratingRow}>
        {RATINGS.map(r => (
          <Pressable
            key={r}
            onPress={() => update('rating', r)}
            style={[s.ratingBtn, form.rating === r && s.ratingBtnOn]}
          >
            <Text style={[s.ratingTxt, form.rating === r && s.ratingTxtOn]}>{r}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={s.editLabel}>Your thoughts (bullet points)</Text>
      <TextInput
        style={[s.editInput, { minHeight: 100, textAlignVertical: 'top' }]}
        value={form.bullet_notes}
        onChangeText={(v) => update('bullet_notes', v)}
        multiline
        placeholder="loved the atmosphere, slow start, great character work"
        placeholderTextColor="#555"
      />
      <Text style={s.editLabel}>Next book title</Text>
      <TextInput style={s.editInput} value={form.next_title} onChangeText={(v) => update('next_title', v)} placeholderTextColor="#555" />
      <Text style={s.editLabel}>Next book author</Text>
      <TextInput style={s.editInput} value={form.next_author} onChangeText={(v) => update('next_author', v)} placeholderTextColor="#555" />
      <View style={{ height: 16 }} />
      <View style={s.row}>
        <ApproveBtn label="Generate Review" onPress={() => onSubmit(form)} disabled={disabled || !canSubmit} />
        <SecondaryBtn label="Cancel" onPress={onCancel} disabled={disabled} />
      </View>
    </View>
  );
}

// ── Review Draft (review) ─────────────────────────────────────────────────────
export function ReviewDraftView({ artifact, onAction, onEdit, disabled }) {
  return (
    <View>
      <Text style={s.sectionTitle}>{artifact.title}</Text>
      <Text style={s.sectionMeta}>by {artifact.author} — {artifact.rating}/5</Text>
      <View style={{ height: 12 }} />
      {artifact.cover_url ? (
        <Image source={{ uri: artifact.cover_url }} style={s.coverImage} resizeMode="contain" />
      ) : null}
      <View style={{ height: 12 }} />
      <Text style={s.editLabel}>Draft review</Text>
      <View style={s.captionBox}>
        <Text selectable style={s.captionText}>{artifact.review_text}</Text>
      </View>
      <View style={{ height: 12 }} />
      <View style={s.row}>
        <ApproveBtn label="Approve" onPress={() => onAction('approve')} disabled={disabled} />
        <SecondaryBtn label="Regenerate" onPress={() => onAction('regenerate')} disabled={disabled} />
      </View>
      <View style={{ height: 10 }} />
      <TertiaryBtn label="Edit review" onPress={onEdit} disabled={disabled} />
    </View>
  );
}

export function ReviewTextEditor({ initial, onSave, onCancel, disabled }) {
  const [text, setText] = useState(initial);
  return (
    <View>
      <Text style={s.sectionTitle}>Edit review</Text>
      <View style={{ height: 10 }} />
      <TextInput
        style={[s.editInput, { minHeight: 200, textAlignVertical: 'top' }]}
        value={text}
        onChangeText={setText}
        multiline
      />
      <View style={{ height: 12 }} />
      <View style={s.row}>
        <ApproveBtn label="Save" onPress={() => onSave(text)} disabled={disabled} />
        <SecondaryBtn label="Cancel" onPress={onCancel} disabled={disabled} />
      </View>
    </View>
  );
}

// ── Small shared buttons ──────────────────────────────────────────────────────
function ApproveBtn({ label, onPress, disabled }) {
  return (
    <Pressable
      style={({ pressed }) => [s.approveBtn, pressed && { opacity: 0.7 }, disabled && { opacity: 0.4 }]}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={s.approveText}>{label}</Text>
    </Pressable>
  );
}

function SecondaryBtn({ label, onPress, disabled }) {
  return (
    <Pressable
      style={({ pressed }) => [s.secondaryBtn, pressed && { opacity: 0.7 }, disabled && { opacity: 0.4 }]}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={s.secondaryText}>{label}</Text>
    </Pressable>
  );
}

function TertiaryBtn({ label, onPress, disabled }) {
  return (
    <Pressable
      style={({ pressed }) => [s.tertiaryBtn, pressed && { opacity: 0.7 }, disabled && { opacity: 0.4 }]}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={s.tertiaryText}>{label}</Text>
    </Pressable>
  );
}

const s = StyleSheet.create({
  sectionTitle: { color: '#fff', fontSize: 20, fontWeight: '700', marginBottom: 4 },
  sectionMeta: { color: '#888', fontSize: 13 },
  card: { backgroundColor: '#1c1c1e', borderRadius: 10, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: '#2a2a2c' },
  cardDate: { color: '#888', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 },
  cardTitle: { color: '#fff', fontSize: 16, fontWeight: '600', marginBottom: 4 },
  cardLine: { color: '#c8c8c8', fontSize: 14 },
  editLabel: { color: '#888', fontSize: 11, textTransform: 'uppercase', marginTop: 8, marginBottom: 4 },
  editInput: { backgroundColor: '#0a0a0a', color: '#fff', borderRadius: 8, padding: 10, fontSize: 14, borderWidth: 1, borderColor: '#2a2a2c' },
  row: { flexDirection: 'row', gap: 10 },
  approveBtn: { flex: 1, backgroundColor: '#30d158', borderRadius: 12, padding: 14, alignItems: 'center' },
  approveText: { color: '#000', fontSize: 16, fontWeight: '700' },
  secondaryBtn: { flex: 1, backgroundColor: '#2a2a2c', borderRadius: 12, padding: 14, alignItems: 'center' },
  secondaryText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  tertiaryBtn: { backgroundColor: 'transparent', borderRadius: 12, padding: 12, alignItems: 'center', borderWidth: 1, borderColor: '#2a2a2c' },
  tertiaryText: { color: '#0a84ff', fontSize: 15, fontWeight: '600' },
  pickRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1c1c1e', borderRadius: 10, padding: 10, marginBottom: 8, borderWidth: 1, borderColor: '#2a2a2c', gap: 12 },
  pickRowSelected: { borderColor: '#30d158' },
  thumb: { width: 48, height: 72, borderRadius: 4, backgroundColor: '#0a0a0a' },
  pickTitle: { color: '#fff', fontSize: 14, fontWeight: '600' },
  pickSub: { color: '#888', fontSize: 12, marginTop: 2 },
  checkbox: { width: 26, height: 26, borderRadius: 6, borderWidth: 1, borderColor: '#444', alignItems: 'center', justifyContent: 'center' },
  checkboxOn: { backgroundColor: '#30d158', borderColor: '#30d158' },
  checkmark: { color: '#000', fontSize: 16, fontWeight: '700' },
  bonusRow: { marginBottom: 6 },
  slidesScroll: { backgroundColor: '#1c1c1e', borderRadius: 10, height: 360 },
  slideImage: { width: 320, height: 360 },
  captionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 4 },
  copyLink: { color: '#0a84ff', fontSize: 13, fontWeight: '600' },
  captionBox: { backgroundColor: '#1c1c1e', borderRadius: 10, padding: 12, borderWidth: 1, borderColor: '#2a2a2c' },
  captionText: { color: '#c8c8c8', fontFamily: 'Menlo', fontSize: 12, lineHeight: 18 },
  coverImage: { width: '100%', height: 220, backgroundColor: '#1c1c1e', borderRadius: 8 },
  ratingRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  ratingBtn: { paddingHorizontal: 10, paddingVertical: 8, backgroundColor: '#1c1c1e', borderRadius: 8, borderWidth: 1, borderColor: '#2a2a2c' },
  ratingBtnOn: { backgroundColor: '#0a84ff', borderColor: '#0a84ff' },
  ratingTxt: { color: '#888', fontSize: 13, fontWeight: '600' },
  ratingTxtOn: { color: '#fff' },
});