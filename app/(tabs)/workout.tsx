import { Ionicons } from '@expo/vector-icons';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { getWorkoutRecommendation as fetchWorkoutRecommendation } from '../../lib/ai';
import { supabase } from '../../lib/supabase';

interface WorkoutLog {
  id: string;
  exercise_name: string;
  sets: number;
  reps: number;
  weight: number;
  notes: string;
  workout_time: string;
}

interface FoodSummary {
  totalCalories: number;
  totalProtein: number;
}

const getLocalDayBounds = () => {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return { startIso: start.toISOString(), endIso: end.toISOString() };
};

export default function WorkoutScreen() {
  const [exerciseName, setExerciseName] = useState('');
  const [sets, setSets] = useState('');
  const [reps, setReps] = useState('');
  const [weight, setWeight] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [workoutLogs, setWorkoutLogs] = useState<WorkoutLog[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [foodSummary, setFoodSummary] = useState<FoodSummary>({ totalCalories: 0, totalProtein: 0 });
  const [aiRecommendation, setAiRecommendation] = useState('');
  const [loadingRecommendation, setLoadingRecommendation] = useState(false);

  const loadTodaysWorkouts = useCallback(async () => {
    setRefreshing(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { startIso, endIso } = getLocalDayBounds();

      const { data, error } = await supabase
        .from('workout_logs')
        .select('*')
        .eq('user_id', user.id)
        .gte('workout_time', startIso)
        .lt('workout_time', endIso)
        .order('workout_time', { ascending: false });

      if (error) {
        console.error('Error loading workouts:', error);
      } else {
        setWorkoutLogs(data || []);
      }
    } finally {
      setRefreshing(false);
    }
  }, []);

  const loadTodaysFood = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) return;

    const { startIso, endIso } = getLocalDayBounds();
    
    const { data, error } = await supabase
      .from('food_logs')
      .select('calories, protein')
      .eq('user_id', user.id)
      .gte('meal_time', startIso)
      .lt('meal_time', endIso);

    if (!error && data) {
      const totalCalories = data.reduce((sum, meal) => sum + meal.calories, 0);
      const totalProtein = data.reduce((sum, meal) => sum + meal.protein, 0);
      setFoodSummary({ totalCalories, totalProtein });
    }
  }, []);

  useEffect(() => {
    loadTodaysWorkouts();
    loadTodaysFood();
  }, [loadTodaysFood, loadTodaysWorkouts]);

  const getAIRecommendation = async () => {
    setLoadingRecommendation(true);
    
    try {
      const recommendation = await fetchWorkoutRecommendation(
        foodSummary.totalCalories,
        foodSummary.totalProtein,
        workoutLogs.length
      );
      setAiRecommendation(recommendation);
    } catch (error) {
      console.error('Recommendation error:', error);
      Alert.alert('Error', 'Could not get AI recommendation');
    } finally {
      setLoadingRecommendation(false);
    }
  };

  const handleSaveWorkout = async () => {
    if (!exerciseName || !sets || !reps) {
      Alert.alert('Error', 'Please enter at least exercise name, sets, and reps');
      return;
    }

    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      Alert.alert('Error', 'Not logged in');
      setLoading(false);
      return;
    }

    const { error } = await supabase.from('workout_logs').insert({
      user_id: user.id,
      exercise_name: exerciseName,
      sets: parseInt(sets) || 0,
      reps: parseInt(reps) || 0,
      weight: parseFloat(weight) || 0,
      notes: notes,
    });

    setLoading(false);

    if (error) {
      Alert.alert('Error', error.message);
    } else {
      Alert.alert('Success', 'Workout logged!');
      // Clear form
      setExerciseName('');
      setSets('');
      setReps('');
      setWeight('');
      setNotes('');
      // Reload workouts
      loadTodaysWorkouts();
    }
  };

  const totalSets = workoutLogs.reduce((sum, log) => sum + log.sets, 0);
  const totalVolume = workoutLogs.reduce((sum, log) => sum + (log.sets * log.reps * log.weight), 0);

  return (
    <ScrollView style={styles.container}>
      {/* Food Summary from Today */}
      <View style={styles.foodSummaryCard}>
        <View style={styles.cardHeader}>
          <Ionicons name="restaurant" size={24} color="#34C759" />
          <Text style={styles.cardTitle}>Today&apos;s Nutrition</Text>
        </View>
        <View style={styles.nutritionRow}>
          <View style={styles.nutritionItem}>
            <Text style={styles.nutritionValue}>{foodSummary.totalCalories}</Text>
            <Text style={styles.nutritionLabel}>Calories</Text>
          </View>
          <View style={styles.nutritionItem}>
            <Text style={styles.nutritionValue}>{foodSummary.totalProtein.toFixed(1)}g</Text>
            <Text style={styles.nutritionLabel}>Protein</Text>
          </View>
        </View>
        
        <TouchableOpacity
          style={styles.aiButton}
          onPress={getAIRecommendation}
          disabled={loadingRecommendation}
        >
          <Ionicons name="bulb" size={20} color="#fff" />
          <Text style={styles.aiButtonText}>
            {loadingRecommendation ? 'Getting recommendation...' : 'Get AI Workout Recommendation'}
          </Text>
        </TouchableOpacity>

        {aiRecommendation && (
          <View style={styles.recommendationBox}>
            <Text style={styles.recommendationTitle}>💪 AI Recommendation:</Text>
            <Text style={styles.recommendationText}>{aiRecommendation}</Text>
          </View>
        )}
      </View>

      {/* Log Workout Form */}
      <View style={styles.formSection}>
        <Text style={styles.sectionTitle}>Log a Workout</Text>
        
        <TextInput
          style={styles.input}
          placeholder="Exercise name (e.g., Bench Press)"
          value={exerciseName}
          onChangeText={setExerciseName}
        />
        
        <View style={styles.row}>
          <TextInput
            style={[styles.input, styles.smallInput]}
            placeholder="Sets"
            value={sets}
            onChangeText={setSets}
            keyboardType="numeric"
          />
          <TextInput
            style={[styles.input, styles.smallInput]}
            placeholder="Reps"
            value={reps}
            onChangeText={setReps}
            keyboardType="numeric"
          />
          <TextInput
            style={[styles.input, styles.smallInput]}
            placeholder="Weight (kg)"
            value={weight}
            onChangeText={setWeight}
            keyboardType="numeric"
          />
        </View>

        <TextInput
          style={[styles.input, styles.notesInput]}
          placeholder="Notes (optional)"
          value={notes}
          onChangeText={setNotes}
          multiline
        />

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleSaveWorkout}
          disabled={loading}
        >
          <Text style={styles.buttonText}>
            {loading ? 'Saving...' : 'Log Workout'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Today's Summary */}
      <View style={styles.summarySection}>
        <Text style={styles.sectionTitle}>Today&apos;s Workout Summary</Text>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Total Sets:</Text>
          <Text style={styles.summaryValue}>{totalSets}</Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Total Volume:</Text>
          <Text style={styles.summaryValue}>{totalVolume.toFixed(0)} kg</Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Exercises:</Text>
          <Text style={styles.summaryValue}>{workoutLogs.length}</Text>
        </View>
      </View>

      {/* Today's Workouts */}
      <View style={styles.logsSection}>
        <Text style={styles.sectionTitle}>Today&apos;s Workouts</Text>
        {refreshing ? (
          <ActivityIndicator size="large" color="#007AFF" />
        ) : workoutLogs.length === 0 ? (
          <Text style={styles.emptyText}>No workouts logged yet today</Text>
        ) : (
          workoutLogs.map((log) => (
            <View key={log.id} style={styles.logCard}>
              <Text style={styles.logExerciseName}>{log.exercise_name}</Text>
              <View style={styles.logDetails}>
                <Text style={styles.logSets}>{log.sets} sets × {log.reps} reps</Text>
                {log.weight > 0 && (
                  <Text style={styles.logWeight}>@ {log.weight}kg</Text>
                )}
              </View>
              {log.notes && (
                <Text style={styles.logNotes}>📝 {log.notes}</Text>
              )}
              <Text style={styles.logTime}>
                {new Date(log.workout_time).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </Text>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  foodSummaryCard: {
    backgroundColor: '#fff',
    padding: 20,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#34C759',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
    gap: 10,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  nutritionRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 15,
  },
  nutritionItem: {
    alignItems: 'center',
  },
  nutritionValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#34C759',
  },
  nutritionLabel: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  aiButton: {
    backgroundColor: '#FF9500',
    padding: 15,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  aiButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  recommendationBox: {
    backgroundColor: '#FFF9E6',
    padding: 15,
    borderRadius: 8,
    marginTop: 15,
    borderLeftWidth: 3,
    borderLeftColor: '#FF9500',
  },
  recommendationTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  recommendationText: {
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
  },
  formSection: {
    backgroundColor: '#fff',
    padding: 20,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 5,
  },
  smallInput: {
    flex: 1,
  },
  notesInput: {
    height: 60,
    textAlignVertical: 'top',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    marginTop: 10,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    textAlign: 'center',
    fontSize: 16,
    fontWeight: '600',
  },
  summarySection: {
    backgroundColor: '#fff',
    padding: 20,
    marginBottom: 10,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 16,
    color: '#666',
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  logsSection: {
    backgroundColor: '#fff',
    padding: 20,
    marginBottom: 20,
  },
  emptyText: {
    textAlign: 'center',
    color: '#999',
    padding: 20,
  },
  logCard: {
    backgroundColor: '#f9f9f9',
    padding: 15,
    borderRadius: 8,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#FF3B30',
  },
  logExerciseName: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  logDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 5,
  },
  logSets: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '600',
  },
  logWeight: {
    fontSize: 14,
    color: '#666',
  },
  logNotes: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
    marginTop: 5,
  },
  logTime: {
    fontSize: 12,
    color: '#999',
    marginTop: 5,
  },
});
