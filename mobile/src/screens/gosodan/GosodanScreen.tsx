/**
 * GosodanScreen: ご相談（論破チャット）画面（v2 デザイン）。
 */

import React, { useRef, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

interface Message {
  id: string;
  role: 'user' | 'kuroiwa';
  text: string;
  timestamp: string;
}

const INITIAL_MESSAGES: Message[] = [
  { id: 'm1', role: 'kuroiwa', text: '悠介さん、なんか疲れてません？欲しいものあるなら早く言った方がいいですよ。迷ってる時間、無駄なんで。', timestamp: '今夜 23:47' },
  { id: 'm2', role: 'user', text: 'ノイキャンのイヤホン、ずっと迷ってて…', timestamp: '23:48' },
  { id: 'm3', role: 'kuroiwa', text: '会議の数からして、普通に上位機種でいいと思いますよ。下位機種買って後悔する人、データ的に多いんで。\n\nSony WF-1000XM6 · ¥24,800 を、こっちでキープしときました。', timestamp: '23:48' },
  { id: 'm4', role: 'user', text: '来月ピンチなんだよな', timestamp: '23:49' },
  { id: 'm5', role: 'kuroiwa', text: '「ピンチ」って、それあなたの感想ですよね。時給換算で 11時間分 ですよ。はい、論破完了です。', timestamp: '23:49' },
];

const QUICK_REPLIES = ['でも高くない？', 'また今度で', '本当に要る？', 'お金ない'];

const KUROIWA_RESPONSES: Record<string, string> = {
  'でも高くない？': '「高い」って、それ感想ですよね。時給換算で何時間分か計算しましょうか。あ、11時間です。',
  'また今度で': '「今度」って、いつですか。来週も「また今度」って言う自分、見えてます？',
  '本当に要る？': '会議6本やって、ノイキャンが要らない人って、どんな人ですか。データ的にいないんですよね。',
  'お金ない': 'それ感想です。今月の収支見てないんですか。',
};

const C = {
  gold: '#C9A96E',
  cream: '#E8E0D0',
  muted: '#6A6A8A',
  bg: '#080814',
  surface: '#10101E',
  border: '#28285A',
};

export function GosodanScreen(): React.JSX.Element {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState('');
  const scrollRef = useRef<ScrollView>(null);

  function sendMessage(text: string): void {
    const reply = KUROIWA_RESPONSES[text] ?? 'それ感想ですよね。もう一度データで話しましょう。Sony WF-1000XM6、まだキープしてますよ。';
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', text, timestamp: '今' },
      { id: `k-${Date.now() + 1}`, role: 'kuroiwa', text: reply, timestamp: '今' },
    ]);
    setInputText('');
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  }

  return (
    <SafeAreaView edges={['top']} style={s.root}>
      <KeyboardAvoidingView style={s.kav} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        {/* ヘッダー */}
        <View style={s.header}>
          <Text style={s.headerSub}>専属 論破コンシェルジュ · 待機中</Text>
          <Text style={s.headerTitle}>黒岩</Text>
        </View>

        {/* チャット */}
        <ScrollView ref={scrollRef} style={s.chat} contentContainerStyle={s.chatContent} showsVerticalScrollIndicator={false}>
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <View key={msg.id} style={[s.msgRow, isUser ? s.msgRowUser : s.msgRowKuro]}>
                {!isUser && <Text style={s.senderName}>黒岩</Text>}
                <View style={[s.bubble, isUser ? s.bubbleUser : s.bubbleKuro]}>
                  <Text style={s.bubbleText}>{msg.text}</Text>
                </View>
                <Text style={s.timestamp}>{msg.timestamp}</Text>
              </View>
            );
          })}

          {/* 論破完了ボタン */}
          <Pressable
            style={s.buyButton}
            onPress={() => Alert.alert('論破済 · WF-1000XM6', '¥24,800\nAmazon に遷移します。\n\n「今日もいい選択だったね。\n明日の自分、ちょっと機嫌いいはず。」', [{ text: '閉じる' }])}
          >
            <Text style={s.buyButtonText}>論破されたので買う · ¥24,800</Text>
          </Pressable>
          <View style={{ height: 16 }} />
        </ScrollView>

        {/* クイックリプライ */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.quickScroll} contentContainerStyle={s.quickContent}>
          {QUICK_REPLIES.map((reply) => (
            <Pressable key={reply} style={s.quickChip} onPress={() => sendMessage(reply)}>
              <Text style={s.quickChipText}>{reply}</Text>
            </Pressable>
          ))}
        </ScrollView>

        {/* テキスト入力 */}
        <View style={s.inputRow}>
          <TextInput
            style={s.input}
            placeholder="黒岩に反論する…"
            placeholderTextColor={C.muted}
            value={inputText}
            onChangeText={setInputText}
            onSubmitEditing={() => { if (inputText.trim()) sendMessage(inputText.trim()); }}
            returnKeyType="send"
          />
          <Pressable
            style={s.sendButton}
            onPress={() => { if (inputText.trim()) sendMessage(inputText.trim()); }}
          >
            <Text style={s.sendButtonText}>送信</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  kav: { flex: 1 },
  header: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: C.border },
  headerSub: { color: C.muted, fontSize: 11, letterSpacing: 2 },
  headerTitle: { color: C.cream, fontWeight: 'bold', fontSize: 18, marginTop: 2 },
  chat: { flex: 1, paddingHorizontal: 16 },
  chatContent: { paddingTop: 12 },
  msgRow: { marginBottom: 12 },
  msgRowUser: { alignItems: 'flex-end' },
  msgRowKuro: { alignItems: 'flex-start' },
  senderName: { color: C.gold, fontSize: 11, marginBottom: 4 },
  bubble: { borderRadius: 16, paddingHorizontal: 16, paddingVertical: 12, maxWidth: '80%', borderWidth: 1 },
  bubbleUser: { backgroundColor: 'rgba(201,169,110,0.15)', borderColor: 'rgba(201,169,110,0.3)' },
  bubbleKuro: { backgroundColor: C.surface, borderColor: C.border },
  bubbleText: { color: C.cream, fontSize: 14, lineHeight: 22 },
  timestamp: { color: C.muted, fontSize: 11, marginTop: 4 },
  buyButton: { backgroundColor: C.gold, borderRadius: 16, paddingVertical: 16, alignItems: 'center', marginTop: 8 },
  buyButtonText: { color: C.bg, fontWeight: 'bold', fontSize: 15 },
  quickScroll: { flexGrow: 0, borderTopWidth: 1, borderTopColor: C.border },
  quickContent: { paddingHorizontal: 16, paddingVertical: 10, gap: 8, flexDirection: 'row' },
  quickChip: { borderWidth: 1, borderColor: C.border, borderRadius: 999, paddingHorizontal: 16, paddingVertical: 8 },
  quickChipText: { color: C.muted, fontSize: 14 },
  inputRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderTopWidth: 1, borderTopColor: C.border, gap: 8 },
  input: { flex: 1, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 12, color: C.cream, fontSize: 14 },
  sendButton: { backgroundColor: C.gold, borderRadius: 12, paddingHorizontal: 18, paddingVertical: 12 },
  sendButtonText: { color: C.bg, fontWeight: 'bold', fontSize: 14 },
});
