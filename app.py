import React, { useState } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  Modal,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  Alert,
  StatusBar
} from 'react-native';

// =========================================================
// [COMPONENT 1] 파인만틱 입력 엔진 (The Simplifier)
// =========================================================
const FeynmanInput = ({ isVisible, onClose, onSave }) => {
  const [concept, setConcept] = useState('');
  const [explanation, setExplanation] = useState('');
  const [engineMessage, setEngineMessage] = useState('💡 전문 용어 대신 쉬운 말로 풀어보세요.');

  // 엔진 로직: 단순화(Simplicity) 체크
  const checkSimplicity = (text) => {
    if (text.length === 0) {
      setEngineMessage('💡 전문 용어 대신 쉬운 말로 풀어보세요.');
    } else if (text.length < 15) {
      setEngineMessage('🤔 흠... 설명이 너무 짧아요. 조금 더 풀어서 써볼까요?');
    } else {
      setEngineMessage('⚡️ 좋습니다! 엔진이 매끄럽게 돌아갑니다.');
    }
  };

  const handleTextChange = (text) => {
    setExplanation(text);
    checkSimplicity(text);
  };

  const handleSave = () => {
    if (!concept.trim()) {
      Alert.alert("엔진 경고", "정의할 개념(키워드)을 입력해주세요.");
      return;
    }
    if (explanation.length < 10) {
      Alert.alert("엔진 경고", "설명이 충분하지 않습니다. '이해했다'는 착각일 수 있습니다.");
      return;
    }
    
    onSave({ 
      id: Date.now().toString(), // 고유 ID 생성
      concept, 
      explanation, 
      date: new Date().toLocaleDateString() 
    });
    
    // 초기화
    setConcept('');
    setExplanation('');
    onClose();
  };

  return (
    <Modal visible={isVisible} animationType="slide" transparent={true} onRequestClose={onClose}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>🧠 지식 변환 엔진</Text>
            <TouchableOpacity onPress={onClose}>
              <Text style={styles.closeButton}>✕</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>1. 무엇을 공부했나요?</Text>
          <TextInput
            style={styles.inputTitle}
            placeholder="예: 양자역학, 마케팅 퍼널..."
            value={concept}
            onChangeText={setConcept}
            placeholderTextColor="#aaa"
          />

          <View style={styles.engineBox}>
            <Text style={styles.engineLabel}>📢 2. 12살 조카에게 설명한다면?</Text>
            <TextInput
              style={styles.inputBody}
              placeholder="가장 쉬운 단어로, 비유를 들어서 설명해보세요."
              value={explanation}
              onChangeText={handleTextChange}
              multiline
              placeholderTextColor="#aaa"
            />
            <Text style={styles.feedbackText}>{engineMessage}</Text>
          </View>

          <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
            <Text style={styles.saveButtonText}>지식 저장 (Save Insight)</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
};

// =========================================================
// [COMPONENT 2] 메인 대시보드 (The Dashboard)
// =========================================================
export default function App() {
  const [modalVisible, setModalVisible] = useState(false);
  const [thoughts, setThoughts] = useState([
    { 
      id: '1', 
      concept: 'FeynmanTic (파인만틱)', 
      explanation: '복잡한 것을 단순하게 설명하지 못하면 모르는 것이다. 이 원리를 이용해 진짜 지식을 만드는 도구.', 
      date: 'Example' 
    }
  ]);

  const addThought = (newThought) => {
    setThoughts(prev => [newThought, ...prev]);
  };

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{item.concept}</Text>
        <Text style={styles.cardDate}>{item.date}</Text>
      </View>
      <Text style={styles.cardBody}>{item.explanation}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      
      {/* 헤더 */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>FeynmanTic Engine</Text>
        <Text style={styles.headerSubtitle}>Thought OS v1.0</Text>
      </View>

      {/* 리스트 영역 */}
      <FlatList
        data={thoughts}
        renderItem={renderItem}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>아직 가동된 엔진이 없습니다.</Text>
            <Text style={styles.emptyText}>아래 버튼을 눌러 생각을 시작하세요.</Text>
          </View>
        }
      />

      {/* 엔진 가동 버튼 (FAB) */}
      <TouchableOpacity 
        style={styles.fab} 
        onPress={() => setModalVisible(true)}
        activeOpacity={0.8}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>

      {/* 엔진 모달 연결 */}
      <FeynmanInput 
        isVisible={modalVisible} 
        onClose={() => setModalVisible(false)} 
        onSave={addThought}
      />
    </SafeAreaView>
  );
}

// =========================================================
// [STYLES] 스타일 정의
// =========================================================
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA', // 차분한 회색 배경
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#1a1a1a',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
    letterSpacing: 1,
  },
  listContent: {
    padding: 20,
    paddingBottom: 100,
  },
  card: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 16,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
    borderLeftWidth: 5,
    borderLeftColor: '#3498db', // 파인만틱 블루
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2c3e50',
  },
  cardDate: {
    fontSize: 12,
    color: '#999',
  },
  cardBody: {
    fontSize: 15,
    lineHeight: 22,
    color: '#555',
  },
  emptyState: {
    marginTop: 50,
    alignItems: 'center',
  },
  emptyText: {
    color: '#aaa',
    fontSize: 16,
    marginBottom: 5,
  },
  fab: {
    position: 'absolute',
    right: 25,
    bottom: 30,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#2c3e50',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  fabText: {
    fontSize: 32,
    color: '#fff',
    marginTop: -2,
  },
  // 모달 스타일
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 25,
    borderTopRightRadius: 25,
    padding: 25,
    minHeight: 500,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -5 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 10,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 25,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  closeButton: {
    fontSize: 24,
    color: '#999',
    padding: 5,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  inputTitle: {
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    padding: 15,
    fontSize: 16,
    marginBottom: 25,
    borderWidth: 1,
    borderColor: '#eee',
  },
  engineBox: {
    backgroundColor: '#eef2f7',
    borderRadius: 12,
    padding: 15,
    marginBottom: 25,
    borderLeftWidth: 4,
    borderLeftColor: '#3498db',
  },
  engineLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: '#2980b9',
    marginBottom: 10,
  },
  inputBody: {
    height: 120,
    textAlignVertical: 'top',
    fontSize: 16,
    lineHeight: 24,
    color: '#333',
  },
  feedbackText: {
    marginTop: 10,
    fontSize: 13,
    fontWeight: '600',
    color: '#e67e22',
    textAlign: 'right',
  },
  saveButton: {
    backgroundColor: '#3498db',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
