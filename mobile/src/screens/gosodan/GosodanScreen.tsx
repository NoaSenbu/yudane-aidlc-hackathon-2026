/**
 * GosodanScreen: ご相談（論破チャット）画面（v2 デザイン）。
 */

import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

const AMAZON_URL = 'https://www.amazon.co.jp/dp/B0GL7VS33K';

interface Message {
  id: string;
  role: 'user' | 'kuroiwa';
  text: string;
  timestamp: string;
}

const QUICK_REPLIES = ['でも高くない？', 'また今度で', '本当に要る？', 'お金ない'];

// スクリプト外のメッセージ（3回目以降）
const KUROIWA_RESPONSE_SETS: Record<string, string[]> = {
  'でも高くない？': [
    '「高い」って、それ感想ですよね。時給換算で何時間分か計算しましょうか。あ、11時間です。',
    'それ、外食何回分ですか。3回ですよね。どっちが豊かか、聞いてもいいですか。',
    '24,800円、高いですか。耳が正気に戻るまで2週間、生産性が落ちた損失よりは少ないですよ。',
  ],
  'また今度で': [
    '「今度」って、いつですか。来週も「また今度」って言う自分、見えてます？',
    '「今度」って言ったのは何回目ですか。私、数えてますよ。',
    'Amazon のカート、放置して2週間。それ、何の決断ですか。',
  ],
  '本当に要る？': [
    '会議6本やって、ノイキャンが要らない人って、どんな人ですか。データ的にいないんですよね。',
    '「要る」か「要らない」かの判断を先送りにすること自体が、要る、の答えですよ。',
    '先週3回カートに入れましたよ。その行動が答えじゃないですか。',
  ],
  'お金ない': [
    'それ感想です。今月の収支見てないんですか。',
    '「お金ない」って言いながら、今月外食いくらですか。',
    '残予算 ¥38,000 ありますよね。どこに「お金ない」があるんでしょう。',
  ],
};

const FALLBACK_RESPONSES = [
  'それ感想ですよね。もう一度データで話しましょう。Sony WF-1000XM6、まだキープしてますよ。',
  'その言い訳、聞いたことあります。でも後悔した人、買った方に一人もいないんですよね。',
  '今夜また悩むんですよね。じゃあ今決めましょう。それがいちばん楽ですよ。',
  '「迷っている」ということは、答えはもう出てるんじゃないですか。',
  'その言い方だと、明日の自分に任せてる感じがしますね。明日の自分、もっと疲れてますよ。',
  'ほかに気になってる理由があれば、話してみてください。全部論破しますよ。',
];

const C = {
  gold: '#C9A96E',
  cream: '#E8E0D0',
  muted: '#6A6A8A',
  bg: '#080814',
  surface: '#10101E',
  border: '#28285A',
};

function pickResponse(text: string): string {
  const set = KUROIWA_RESPONSE_SETS[text];
  if (set) return set[Math.floor(Math.random() * set.length)] ?? set[0] ?? '';
  return FALLBACK_RESPONSES[Math.floor(Math.random() * FALLBACK_RESPONSES.length)] ?? '';
}

export function GosodanScreen(): React.JSX.Element {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [userMsgCount, setUserMsgCount] = useState(0);
  const [showBuyButton, setShowBuyButton] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  // 画面オープン時に黒岩から挨拶
  useEffect(() => {
    setIsTyping(true);
    const timer = setTimeout(() => {
      setIsTyping(false);
      setMessages([{
        id: 'k-open',
        role: 'kuroiwa',
        text: '悠介さんなんか疲れてません？欲しいものあったら買ったほうがいいですよ？迷ってる時間無駄なんで。',
        timestamp: '今',
      }]);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  function sendMessage(text: string): void {
    if (isTyping) return;

    const newCount = userMsgCount + 1;
    setUserMsgCount(newCount);
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', text, timestamp: '今' },
    ]);
    setInputText('');
    setIsTyping(true);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);

    setTimeout(() => {
      let reply: string;
      if (newCount === 1) {
        reply = '会議の数からして、普通に上位機種でいいと思いますよ。下位機種買って後悔する人、データ的に多いんで。';
      } else if (newCount === 2) {
        reply = 'それってあなたの感想ですよね。はい、論破';
      } else {
        reply = pickResponse(text);
      }
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        { id: `k-${Date.now()}`, role: 'kuroiwa', text: reply, timestamp: '今' },
      ]);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
      if (newCount === 2) {
        setTimeout(() => {
          setShowBuyButton(true);
          setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
        }, 4000);
      }
    }, 2000);
  }

  return (
    <SafeAreaView edges={['top']} style={s.root}>
      <KeyboardAvoidingView style={s.kav} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        {/* ヘッダー */}
        <View style={s.header}>
          <Text style={s.headerSub}>
            専属 論破コンシェルジュ · {isTyping ? '入力中…' : '待機中'}
          </Text>
          <Text style={s.headerTitle}>黒岩</Text>
        </View>

        {/* チャット */}
        <ScrollView
          ref={scrollRef}
          style={s.chat}
          contentContainerStyle={s.chatContent}
          showsVerticalScrollIndicator={false}
        >
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

          {/* タイピングインジケーター */}
          {isTyping && (
            <View style={[s.msgRow, s.msgRowKuro]}>
              <Text style={s.senderName}>黒岩</Text>
              <View style={[s.bubble, s.bubbleKuro, s.typingBubble]}>
                <ActivityIndicator color={C.gold} size="small" />
              </View>
            </View>
          )}

          {/* 購入ボタン（論破後4秒で表示） */}
          {showBuyButton && (
            <Pressable
              style={s.buyButton}
              onPress={() => void Linking.openURL(AMAZON_URL)}
            >
              <Text style={s.buyButtonText}>論破されたので買う · ¥24,800</Text>
            </Pressable>
          )}
          <View style={{ height: 16 }} />
        </ScrollView>

        {/* クイックリプライ */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={s.quickScroll}
          contentContainerStyle={s.quickContent}
        >
          {QUICK_REPLIES.map((reply) => (
            <Pressable
              key={reply}
              style={[s.quickChip, isTyping && s.quickChipDisabled]}
              disabled={isTyping}
              onPress={() => sendMessage(reply)}
            >
              <Text style={[s.quickChipText, isTyping && s.quickChipTextDisabled]}>{reply}</Text>
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
            onSubmitEditing={() => {
              if (inputText.trim()) sendMessage(inputText.trim());
            }}
            returnKeyType="send"
            editable={!isTyping}
          />
          <Pressable
            style={[s.sendButton, isTyping && s.sendButtonDisabled]}
            disabled={isTyping}
            onPress={() => {
              if (inputText.trim()) sendMessage(inputText.trim());
            }}
          >
            <Text style={s.sendButtonText}>送信</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root:                 { flex: 1, backgroundColor: C.bg },
  kav:                  { flex: 1 },
  header:               { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: C.border },
  headerSub:            { color: C.muted, fontSize: 11, letterSpacing: 2 },
  headerTitle:          { color: C.cream, fontWeight: 'bold', fontSize: 18, marginTop: 2 },
  chat:                 { flex: 1, paddingHorizontal: 16 },
  chatContent:          { paddingTop: 12 },
  msgRow:               { marginBottom: 12 },
  msgRowUser:           { alignItems: 'flex-end' },
  msgRowKuro:           { alignItems: 'flex-start' },
  senderName:           { color: C.gold, fontSize: 11, marginBottom: 4 },
  bubble:               { borderRadius: 16, paddingHorizontal: 16, paddingVertical: 12, maxWidth: '80%', borderWidth: 1 },
  bubbleUser:           { backgroundColor: 'rgba(201,169,110,0.15)', borderColor: 'rgba(201,169,110,0.3)' },
  bubbleKuro:           { backgroundColor: C.surface, borderColor: C.border },
  bubbleText:           { color: C.cream, fontSize: 14, lineHeight: 22 },
  typingBubble:         { paddingHorizontal: 20, paddingVertical: 14 },
  timestamp:            { color: C.muted, fontSize: 11, marginTop: 4 },
  buyButton:            { backgroundColor: C.gold, borderRadius: 16, paddingVertical: 16, alignItems: 'center', marginTop: 8 },
  buyButtonText:        { color: C.bg, fontWeight: 'bold', fontSize: 15 },
  quickScroll:          { flexGrow: 0, borderTopWidth: 1, borderTopColor: C.border },
  quickContent:         { paddingHorizontal: 16, paddingVertical: 10, gap: 8, flexDirection: 'row' },
  quickChip:            { borderWidth: 1, borderColor: C.border, borderRadius: 999, paddingHorizontal: 16, paddingVertical: 8 },
  quickChipDisabled:    { opacity: 0.4 },
  quickChipText:        { color: C.muted, fontSize: 14 },
  quickChipTextDisabled: { color: C.muted },
  inputRow:             { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderTopWidth: 1, borderTopColor: C.border, gap: 8 },
  input:                { flex: 1, backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 12, color: C.cream, fontSize: 14 },
  sendButton:           { backgroundColor: C.gold, borderRadius: 12, paddingHorizontal: 18, paddingVertical: 12 },
  sendButtonDisabled:   { opacity: 0.4 },
  sendButtonText:       { color: C.bg, fontWeight: 'bold', fontSize: 14 },
});
