import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { analyzeFoodImage as analyzeFoodImageWithAI } from '../../lib/ai';
import { supabase } from '../../lib/supabase';

interface FoodLog {
  id: string;
  meal_name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  meal_time: string;
  meal_category: string;
}

const getLocalDayBounds = () => {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return { startIso: start.toISOString(), endIso: end.toISOString() };
};

export default function FoodScreen() {
  const [mealName, setMealName] = useState('');
  const [calories, setCalories] = useState('');
  const [protein, setProtein] = useState('');
  const [carbs, setCarbs] = useState('');
  const [fat, setFat] = useState('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [foodLogs, setFoodLogs] = useState<FoodLog[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const loadTodaysMeals = useCallback(async () => {
    setRefreshing(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { startIso, endIso } = getLocalDayBounds();

      const { data, error } = await supabase
        .from('food_logs')
        .select('*')
        .eq('user_id', user.id)
        .gte('meal_time', startIso)
        .lt('meal_time', endIso)
        .order('meal_time', { ascending: false });

      if (error) {
        console.error('Error loading meals:', error);
      } else {
        setFoodLogs(data || []);
      }
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadTodaysMeals();
  }, [loadTodaysMeals]);

  const analyzeImage = async (imageUri: string) => {
    setAnalyzing(true);
    
    try {
      // Convert image to base64
      const response = await fetch(imageUri);
      const blob = await response.blob();
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const result = reader.result as string;
          // Remove data URL prefix to get just the base64 data
          const base64Data = result.split(',')[1];
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });

      const nutritionData = await analyzeFoodImageWithAI(base64, 'image/jpeg');

      // Auto-fill the form
      setMealName(nutritionData.meal_name);
      setCalories(nutritionData.calories.toString());
      setProtein(nutritionData.protein.toString());
      setCarbs(nutritionData.carbs.toString());
      setFat(nutritionData.fat.toString());

      Alert.alert('Success!', 'Food analyzed! Review the values and tap Log Meal to save.');
    } catch (error) {
      console.error('Analysis error:', error);
      Alert.alert('Error', 'Could not analyze image. Please enter manually.');
    } finally {
      setAnalyzing(false);
    }
  };

  const takePicture = async () => {
    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Camera permission is required to take photos');
      return;
    }

    // Launch camera
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.5,
      base64: false,
    });

    if (!result.canceled && result.assets[0]) {
      setSelectedImage(result.assets[0].uri);
      await analyzeImage(result.assets[0].uri);
    }
  };

  const pickImage = async () => {
    // Request media library permissions
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Photo library permission is required');
      return;
    }

    // Launch image picker
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.5,
      base64: false,
    });

    if (!result.canceled && result.assets[0]) {
      setSelectedImage(result.assets[0].uri);
      await analyzeImage(result.assets[0].uri);
    }
  };

  const getMealCategory = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return 'Breakfast';
    if (hour >= 12 && hour < 17) return 'Lunch';
    if (hour >= 17 && hour < 22) return 'Dinner';
    return 'Snack';
  };

  const handleSaveMeal = async () => {
    if (!mealName || !calories) {
      Alert.alert('Error', 'Please enter at least meal name and calories');
      return;
    }

    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      Alert.alert('Error', 'Not logged in');
      setLoading(false);
      return;
    }

    const mealCategory = getMealCategory();

    const { error } = await supabase.from('food_logs').insert({
      user_id: user.id,
      meal_name: mealName,
      calories: parseInt(calories) || 0,
      protein: parseFloat(protein) || 0,
      carbs: parseFloat(carbs) || 0,
      fat: parseFloat(fat) || 0,
      meal_category: mealCategory,
    });

    setLoading(false);

    if (error) {
      Alert.alert('Error', error.message);
    } else {
      Alert.alert('Success', `${mealCategory} logged!`);
      // Clear form
      setMealName('');
      setCalories('');
      setProtein('');
      setCarbs('');
      setFat('');
      setSelectedImage(null);
      // Reload meals
      loadTodaysMeals();
    }
  };

  const totalCalories = foodLogs.reduce((sum, log) => sum + log.calories, 0);
  const totalProtein = foodLogs.reduce((sum, log) => sum + log.protein, 0);

  // Group meals by category
  const groupedMeals = {
    Breakfast: foodLogs.filter(log => log.meal_category === 'Breakfast'),
    Lunch: foodLogs.filter(log => log.meal_category === 'Lunch'),
    Dinner: foodLogs.filter(log => log.meal_category === 'Dinner'),
    Snack: foodLogs.filter(log => log.meal_category === 'Snack' || !log.meal_category),
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.formSection}>
        <Text style={styles.sectionTitle}>Log a Meal</Text>
        
        {/* Camera Buttons */}
        <View style={styles.cameraButtons}>
          <TouchableOpacity 
            style={styles.cameraButton}
            onPress={takePicture}
            disabled={analyzing}
          >
            <Ionicons name="camera" size={24} color="#fff" />
            <Text style={styles.cameraButtonText}>Take Photo</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={[styles.cameraButton, styles.galleryButton]}
            onPress={pickImage}
            disabled={analyzing}
          >
            <Ionicons name="images" size={24} color="#fff" />
            <Text style={styles.cameraButtonText}>Choose Photo</Text>
          </TouchableOpacity>
        </View>

        {/* Show selected image */}
        {selectedImage && (
          <Image source={{ uri: selectedImage }} style={styles.previewImage} />
        )}

        {/* Show analyzing indicator */}
        {analyzing && (
          <View style={styles.analyzingContainer}>
            <ActivityIndicator size="large" color="#007AFF" />
            <Text style={styles.analyzingText}>Analyzing food...</Text>
          </View>
        )}
        
        {/* Manual Entry Form */}
        <Text style={styles.orText}>Or enter manually:</Text>
        
        <TextInput
          style={styles.input}
          placeholder="Meal name (e.g., Chicken Biryani)"
          value={mealName}
          onChangeText={setMealName}
        />
        
        <TextInput
          style={styles.input}
          placeholder="Calories"
          value={calories}
          onChangeText={setCalories}
          keyboardType="numeric"
        />
        
        <View style={styles.row}>
          <TextInput
            style={[styles.input, styles.smallInput]}
            placeholder="Protein (g)"
            value={protein}
            onChangeText={setProtein}
            keyboardType="numeric"
          />
          <TextInput
            style={[styles.input, styles.smallInput]}
            placeholder="Carbs (g)"
            value={carbs}
            onChangeText={setCarbs}
            keyboardType="numeric"
          />
          <TextInput
            style={[styles.input, styles.smallInput]}
            placeholder="Fat (g)"
            value={fat}
            onChangeText={setFat}
            keyboardType="numeric"
          />
        </View>

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleSaveMeal}
          disabled={loading}
        >
          <Text style={styles.buttonText}>
            {loading ? 'Saving...' : 'Log Meal'}
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.summarySection}>
        <Text style={styles.sectionTitle}>Today&apos;s Summary</Text>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Total Calories:</Text>
          <Text style={styles.summaryValue}>{totalCalories}</Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Total Protein:</Text>
          <Text style={styles.summaryValue}>{totalProtein.toFixed(1)}g</Text>
        </View>
      </View>

      <View style={styles.logsSection}>
        <Text style={styles.sectionTitle}>Today&apos;s Meals</Text>
        {refreshing ? (
          <ActivityIndicator size="large" color="#007AFF" />
        ) : foodLogs.length === 0 ? (
          <Text style={styles.emptyText}>No meals logged yet today</Text>
        ) : (
          <>
            {/* Breakfast */}
            {groupedMeals.Breakfast.length > 0 && (
              <View style={styles.mealCategory}>
                <Text style={styles.categoryTitle}>🍳 Breakfast</Text>
                {groupedMeals.Breakfast.map((log) => (
                  <View key={log.id} style={styles.logCard}>
                    <Text style={styles.logMealName}>{log.meal_name}</Text>
                    <View style={styles.logDetails}>
                      <Text style={styles.logCalories}>{log.calories} cal</Text>
                      <Text style={styles.logMacros}>
                        P: {log.protein}g | C: {log.carbs}g | F: {log.fat}g
                      </Text>
                    </View>
                    <Text style={styles.logTime}>
                      {new Date(log.meal_time).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {/* Lunch */}
            {groupedMeals.Lunch.length > 0 && (
              <View style={styles.mealCategory}>
                <Text style={styles.categoryTitle}>🥗 Lunch</Text>
                {groupedMeals.Lunch.map((log) => (
                  <View key={log.id} style={styles.logCard}>
                    <Text style={styles.logMealName}>{log.meal_name}</Text>
                    <View style={styles.logDetails}>
                      <Text style={styles.logCalories}>{log.calories} cal</Text>
                      <Text style={styles.logMacros}>
                        P: {log.protein}g | C: {log.carbs}g | F: {log.fat}g
                      </Text>
                    </View>
                    <Text style={styles.logTime}>
                      {new Date(log.meal_time).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {/* Dinner */}
            {groupedMeals.Dinner.length > 0 && (
              <View style={styles.mealCategory}>
                <Text style={styles.categoryTitle}>🍽️ Dinner</Text>
                {groupedMeals.Dinner.map((log) => (
                  <View key={log.id} style={styles.logCard}>
                    <Text style={styles.logMealName}>{log.meal_name}</Text>
                    <View style={styles.logDetails}>
                      <Text style={styles.logCalories}>{log.calories} cal</Text>
                      <Text style={styles.logMacros}>
                        P: {log.protein}g | C: {log.carbs}g | F: {log.fat}g
                      </Text>
                    </View>
                    <Text style={styles.logTime}>
                      {new Date(log.meal_time).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {/* Snacks */}
            {groupedMeals.Snack.length > 0 && (
              <View style={styles.mealCategory}>
                <Text style={styles.categoryTitle}>🍿 Snacks</Text>
                {groupedMeals.Snack.map((log) => (
                  <View key={log.id} style={styles.logCard}>
                    <Text style={styles.logMealName}>{log.meal_name}</Text>
                    <View style={styles.logDetails}>
                      <Text style={styles.logCalories}>{log.calories} cal</Text>
                      <Text style={styles.logMacros}>
                        P: {log.protein}g | C: {log.carbs}g | F: {log.fat}g
                      </Text>
                    </View>
                    <Text style={styles.logTime}>
                      {new Date(log.meal_time).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </>
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
  cameraButtons: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 15,
  },
  cameraButton: {
    flex: 1,
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  galleryButton: {
    backgroundColor: '#34C759',
  },
  cameraButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  previewImage: {
    width: '100%',
    height: 200,
    borderRadius: 8,
    marginBottom: 15,
  },
  analyzingContainer: {
    padding: 20,
    alignItems: 'center',
  },
  analyzingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#007AFF',
  },
  orText: {
    textAlign: 'center',
    color: '#666',
    marginVertical: 10,
    fontSize: 14,
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
  mealCategory: {
    marginBottom: 20,
  },
  categoryTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
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
    borderLeftColor: '#007AFF',
  },
  logMealName: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  logDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 5,
  },
  logCalories: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '600',
  },
  logMacros: {
    fontSize: 14,
    color: '#666',
  },
  logTime: {
    fontSize: 12,
    color: '#999',
  },
});
