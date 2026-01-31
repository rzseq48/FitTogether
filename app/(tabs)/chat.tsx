import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { supabase } from '../../lib/supabase';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface UserContext {
  todayCalories: number;
  todayProtein: number;
  todayMeals: number;
  todayWorkouts: number;
  recentMeals: string[];
  recentWorkouts: string[];
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [userContext, setUserContext] = useState<UserContext | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);

  useEffect(() => {
    loadUserContext();
    addWelcomeMessage();
  }, []);

  const addWelcomeMessage = () => {
    const welcomeMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: "👋 Hey! I'm your AI fitness coach. I can help you with:\n\n• Nutrition advice based on what you've eaten\n• Workout suggestions\n• Answer fitness questions\n• Analyze your progress\n\nWhat would you like to know?",
      timestamp: new Date(),
    };
    setMessages([welcomeMessage]);
  };

  const loadUserContext = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    const today = new Date().toISOString().split('T')[0];

    // Get today's food
    const { data: foodData } = await supabase
      .from('food_logs')
      .select('meal_name, calories, protein')
      .eq('user_id', user.id)
      .gte('meal_time', `${today}T00:00:00`)
      .order('meal_time', { ascending: false });

    // Get today's workouts
    const { data: workoutData } = await supabase
      .from('workout_logs')
      .select('exercise_name, sets, reps, weight')
      .eq('user_id', user.id)
      .gte('workout_time', `${today}T00:00:00`)
      .order('workout_time', { ascending: false });

    const context: UserContext = {
      todayCalories: foodData?.reduce((sum, meal) => sum + meal.calories, 0) || 0,
      todayProtein: foodData?.reduce((sum, meal) => sum + meal.protein, 0) || 0,
      todayMeals: foodData?.length || 0,
      todayWorkouts: workoutData?.length || 0,
      recentMeals: foodData?.slice(0, 5).map(m => m.meal_name) || [],
      recentWorkouts: workoutData?.slice(0, 5).map(w => 
        `${w.exercise_name} ${w.sets}x${w.reps}${w.weight ? ` @${w.weight}kg` : ''}`
      ) || [],
    };

    setUserContext(context);
  };

  const sendMessage = async () => {
    if (!inputText.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setLoading(true);

    try {
      const apiKey = process.env.EXPO_PUBLIC_CLAUDE_API_KEY;

      // Build context for Claude
      let contextPrompt = `You are a knowledgeable fitness and nutrition coach. Be helpful, encouraging, and specific.

User's context today:
- Calories consumed: ${userContext?.todayCalories || 0}
- Protein consumed: ${userContext?.todayProtein || 0}g
- Meals logged: ${userContext?.todayMeals || 0}
- Workouts completed: ${userContext?.todayWorkouts || 0}`;

      if (userContext && userContext.recentMeals.length > 0) {
        contextPrompt += `\n\nRecent meals: ${userContext.recentMeals.join(', ')}`;
      }

      if (userContext && userContext.recentWorkouts.length > 0) {
        contextPrompt += `\n\nRecent workouts: ${userContext.recentWorkouts.join(', ')}`;
      }

      contextPrompt += `\n\nUser's question: ${inputText}

Provide a helpful, personalized response in 2-3 paragraphs. Be conversational and encouraging.`;

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey!,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-3-haiku-20240307',
          max_tokens: 500,
          messages: [
            {
              role: 'user',
              content: contextPrompt,
            },
          ],
        }),
      });

      const data = await response.json();

      if (data.content && data.content[0] && data.content[0].text) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.content[0].text,
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Sorry, I couldn't process that. Please try again!",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      // Scroll to bottom
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  };

  const quickQuestions = [
    "Should I eat more protein?",
    "Is my workout volume enough?",
    "What should I eat after workout?",
    "How can I build muscle?",
  ];

  const handleQuickQuestion = (question: string) => {
    setInputText(question);
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={100}
    >
      {/* Chat History */}
      <ScrollView 
        ref={scrollViewRef}
        style={styles.chatContainer}
        contentContainerStyle={styles.chatContent}
        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((message) => (
          <View
            key={message.id}
            style={[
              styles.messageBubble,
              message.role === 'user' ? styles.userBubble : styles.assistantBubble,
            ]}
          >
            <Text
              style={[
                styles.messageText,
                message.role === 'user' ? styles.userText : styles.assistantText,
              ]}
            >
              {message.content}
            </Text>
            <Text style={styles.timestamp}>
              {message.timestamp.toLocaleTimeString([], { 
                hour: '2-digit', 
                minute: '2-digit' 
              })}
            </Text>
          </View>
        ))}

        {loading && (
          <View style={[styles.messageBubble, styles.assistantBubble]}>
            <ActivityIndicator size="small" color="#007AFF" />
            <Text style={styles.loadingText}>Thinking...</Text>
          </View>
        )}
      </ScrollView>

      {/* Quick Questions */}
      {messages.length <= 1 && !loading && (
        <ScrollView 
          horizontal 
          style={styles.quickQuestionsContainer}
          showsHorizontalScrollIndicator={false}
        >
          {quickQuestions.map((question, index) => (
            <TouchableOpacity
              key={index}
              style={styles.quickQuestionButton}
              onPress={() => handleQuickQuestion(question)}
            >
              <Text style={styles.quickQuestionText}>{question}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Input Area */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Ask me anything about fitness..."
          value={inputText}
          onChangeText={setInputText}
          multiline
          maxLength={500}
        />
        <TouchableOpacity
          style={[styles.sendButton, (!inputText.trim() || loading) && styles.sendButtonDisabled]}
          onPress={sendMessage}
          disabled={!inputText.trim() || loading}
        >
          <Ionicons 
            name="send" 
            size={24} 
            color={(!inputText.trim() || loading) ? '#ccc' : '#fff'} 
          />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  chatContainer: {
    flex: 1,
  },
  chatContent: {
    padding: 15,
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
    marginBottom: 10,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#007AFF',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#fff',
  },
  assistantText: {
    color: '#333',
  },
  timestamp: {
    fontSize: 10,
    color: '#999',
    marginTop: 5,
    alignSelf: 'flex-end',
  },
  loadingText: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
    marginLeft: 10,
  },
  quickQuestionsContainer: {
    paddingHorizontal: 15,
    paddingVertical: 10,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  quickQuestionButton: {
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 20,
    marginRight: 10,
  },
  quickQuestionText: {
    color: '#007AFF',
    fontSize: 14,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 15,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    alignItems: 'flex-end',
  },
  input: {
    flex: 1,
    backgroundColor: '#f0f0f0',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 10,
    maxHeight: 100,
    fontSize: 16,
    marginRight: 10,
  },
  sendButton: {
    backgroundColor: '#007AFF',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#e0e0e0',
  },
});