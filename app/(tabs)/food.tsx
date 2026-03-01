import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ImageBackground,
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

const mealCategoryConfig = [
  { key: 'Breakfast', title: 'Breakfast', emoji: '🍳' },
  { key: 'Lunch', title: 'Lunch', emoji: '🥗' },
  { key: 'Dinner', title: 'Dinner', emoji: '🍽️' },
  { key: 'Snack', title: 'Snacks', emoji: '🍿' },
] as const;

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
  const totalCarbs = foodLogs.reduce((sum, log) => sum + log.carbs, 0);
  const totalFat = foodLogs.reduce((sum, log) => sum + log.fat, 0);

  // Group meals by category
  const groupedMeals = {
    Breakfast: foodLogs.filter(log => log.meal_category === 'Breakfast'),
    Lunch: foodLogs.filter(log => log.meal_category === 'Lunch'),
    Dinner: foodLogs.filter(log => log.meal_category === 'Dinner'),
    Snack: foodLogs.filter(log => log.meal_category === 'Snack' || !log.meal_category),
  };

  const formatMealTime = (mealTime: string) =>
    new Date(mealTime).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

  return (
    <ImageBackground
      source={require('../../assets/images/food-background.png')}
      resizeMode="cover"
      style={styles.screen}
      imageStyle={styles.backgroundImage}
    >
      <View pointerEvents="none" style={styles.photoTint} />
      <View pointerEvents="none" style={styles.backgroundLayer}>
        <View style={[styles.bgBlob, styles.bgBlobTomato]} />
        <View style={[styles.bgBlob, styles.bgBlobAvocado]} />
        <View style={[styles.bgBlob, styles.bgBlobCream]} />
        <Text style={[styles.bgEmoji, styles.bgEmojiTopLeft]}>🥑</Text>
        <Text style={[styles.bgEmoji, styles.bgEmojiTopRight]}>🍊</Text>
        <Text style={[styles.bgEmoji, styles.bgEmojiBottomLeft]}>🥗</Text>
        <Text style={[styles.bgEmoji, styles.bgEmojiBottomRight]}>🍓</Text>
      </View>

      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.contentContainer}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.heroCard}>
          <View style={styles.heroHeader}>
            <View>
              <Text style={styles.heroOverline}>TODAY</Text>
              <Text style={styles.heroTitle}>Food Overview</Text>
            </View>
            <View style={styles.heroBadge}>
              <Ionicons name="nutrition-outline" size={18} color="#0A7C52" />
              <Text style={styles.heroBadgeText}>{foodLogs.length} meals</Text>
            </View>
          </View>

          <View style={styles.heroMainStat}>
            <Text style={styles.heroCalories}>{totalCalories}</Text>
            <Text style={styles.heroCaloriesLabel}>kcal consumed</Text>
          </View>

          <View style={styles.macroPillsRow}>
            <View style={[styles.macroPill, styles.proteinPill]}>
              <Text style={styles.macroPillValue}>{totalProtein.toFixed(1)}g</Text>
              <Text style={styles.macroPillLabel}>Protein</Text>
            </View>
            <View style={[styles.macroPill, styles.carbPill]}>
              <Text style={styles.macroPillValue}>{totalCarbs.toFixed(1)}g</Text>
              <Text style={styles.macroPillLabel}>Carbs</Text>
            </View>
            <View style={[styles.macroPill, styles.fatPill]}>
              <Text style={styles.macroPillValue}>{totalFat.toFixed(1)}g</Text>
              <Text style={styles.macroPillLabel}>Fat</Text>
            </View>
          </View>
        </View>

        <View style={styles.formSection}>
          <Text style={styles.sectionTitle}>Log a Meal</Text>
          <Text style={styles.sectionSubtitle}>Snap a photo or enter nutrition details manually.</Text>
          
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

        <View style={styles.logsSection}>
          <Text style={styles.sectionTitle}>Today&apos;s Meals</Text>
          <Text style={styles.sectionSubtitle}>Grouped by meal time for quick scanning.</Text>
          {refreshing ? (
            <ActivityIndicator size="large" color="#0A7C52" />
          ) : foodLogs.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="restaurant-outline" size={28} color="#93A09A" />
              <Text style={styles.emptyText}>No meals logged yet today</Text>
            </View>
          ) : (
            <>
              {mealCategoryConfig.map((category) => {
                const categoryMeals = groupedMeals[category.key];
                if (categoryMeals.length === 0) return null;

                return (
                  <View key={category.key} style={styles.mealCategory}>
                    <Text style={styles.categoryTitle}>{category.emoji} {category.title}</Text>
                    {categoryMeals.map((log) => (
                      <View key={log.id} style={styles.logCard}>
                        <View style={styles.logTopRow}>
                          <Text style={styles.logMealName}>{log.meal_name}</Text>
                          <Text style={styles.logTime}>{formatMealTime(log.meal_time)}</Text>
                        </View>
                        <Text style={styles.logCalories}>{log.calories} cal</Text>
                        <View style={styles.logMacroChips}>
                          <Text style={styles.logMacroChip}>P {log.protein}g</Text>
                          <Text style={styles.logMacroChip}>C {log.carbs}g</Text>
                          <Text style={styles.logMacroChip}>F {log.fat}g</Text>
                        </View>
                      </View>
                    ))}
                  </View>
                );
              })}
            </>
          )}
        </View>
      </ScrollView>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#F7F2E8',
  },
  backgroundImage: {
    opacity: 0.35,
  },
  photoTint: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#F9F3EA',
    opacity: 0.7,
  },
  backgroundLayer: {
    ...StyleSheet.absoluteFillObject,
  },
  bgBlob: {
    position: 'absolute',
    borderRadius: 999,
    opacity: 0.28,
  },
  bgBlobTomato: {
    width: 320,
    height: 320,
    backgroundColor: '#FFC9A4',
    top: -90,
    right: -110,
  },
  bgBlobAvocado: {
    width: 280,
    height: 280,
    backgroundColor: '#C8E8CC',
    top: 240,
    left: -140,
  },
  bgBlobCream: {
    width: 340,
    height: 340,
    backgroundColor: '#FFEAB4',
    bottom: -150,
    right: -110,
  },
  bgEmoji: {
    position: 'absolute',
    fontSize: 24,
    opacity: 0.14,
  },
  bgEmojiTopLeft: {
    top: 84,
    left: 28,
  },
  bgEmojiTopRight: {
    top: 190,
    right: 26,
  },
  bgEmojiBottomLeft: {
    bottom: 188,
    left: 30,
  },
  bgEmojiBottomRight: {
    bottom: 62,
    right: 28,
  },
  container: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 28,
    gap: 14,
  },
  heroCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: '#DDE7E1',
    shadowColor: '#0A3828',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.06,
    shadowRadius: 14,
    elevation: 2,
  },
  heroHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  heroOverline: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.1,
    color: '#6C7F76',
  },
  heroTitle: {
    marginTop: 4,
    fontSize: 24,
    fontWeight: '800',
    color: '#10221A',
  },
  heroBadge: {
    backgroundColor: '#E8F4ED',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 7,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  heroBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#0A7C52',
  },
  heroMainStat: {
    marginTop: 18,
    marginBottom: 14,
  },
  heroCalories: {
    fontSize: 42,
    fontWeight: '800',
    color: '#10221A',
  },
  heroCaloriesLabel: {
    marginTop: -2,
    fontSize: 14,
    color: '#5F736A',
    fontWeight: '600',
  },
  macroPillsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  macroPill: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderWidth: 1,
  },
  proteinPill: {
    backgroundColor: '#EAF4FF',
    borderColor: '#D1E8FF',
  },
  carbPill: {
    backgroundColor: '#FFF5E8',
    borderColor: '#FFE4C0',
  },
  fatPill: {
    backgroundColor: '#F8EEFF',
    borderColor: '#E9D9FF',
  },
  macroPillValue: {
    fontSize: 15,
    fontWeight: '800',
    color: '#10221A',
  },
  macroPillLabel: {
    marginTop: 2,
    fontSize: 12,
    color: '#5F736A',
  },
  formSection: {
    backgroundColor: '#FFFFFF',
    padding: 18,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#DDE7E1',
  },
  sectionTitle: {
    fontSize: 21,
    fontWeight: '800',
    color: '#10221A',
  },
  sectionSubtitle: {
    marginTop: 6,
    marginBottom: 14,
    fontSize: 13,
    color: '#6A7D74',
    lineHeight: 18,
  },
  cameraButtons: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  cameraButton: {
    flex: 1,
    backgroundColor: '#0A7C52',
    padding: 14,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  galleryButton: {
    backgroundColor: '#1660B8',
  },
  cameraButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
  previewImage: {
    width: '100%',
    height: 200,
    borderRadius: 14,
    marginBottom: 14,
  },
  analyzingContainer: {
    padding: 18,
    alignItems: 'center',
    backgroundColor: '#F6FBF8',
    borderRadius: 12,
    marginBottom: 8,
  },
  analyzingText: {
    marginTop: 10,
    fontSize: 15,
    color: '#0A7C52',
    fontWeight: '600',
  },
  orText: {
    textAlign: 'center',
    color: '#6A7D74',
    marginVertical: 12,
    fontSize: 13,
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#D5E0DA',
    padding: 12,
    borderRadius: 12,
    marginBottom: 10,
    fontSize: 16,
    backgroundColor: '#FCFDFC',
    color: '#10221A',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 8,
  },
  smallInput: {
    flex: 1,
  },
  button: {
    backgroundColor: '#0A7C52',
    padding: 15,
    borderRadius: 12,
    marginTop: 12,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    textAlign: 'center',
    fontSize: 16,
    fontWeight: '700',
  },
  logsSection: {
    backgroundColor: '#FFFFFF',
    padding: 18,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#DDE7E1',
  },
  mealCategory: {
    marginTop: 12,
    marginBottom: 10,
  },
  categoryTitle: {
    fontSize: 17,
    fontWeight: '800',
    marginBottom: 10,
    color: '#1D2B24',
  },
  emptyState: {
    paddingVertical: 24,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  emptyText: {
    textAlign: 'center',
    color: '#7C8E85',
    fontSize: 14,
  },
  logCard: {
    backgroundColor: '#F8FBF9',
    padding: 13,
    borderRadius: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#E0EAE4',
  },
  logTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  logMealName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A2A22',
    flex: 1,
    marginRight: 8,
  },
  logCalories: {
    fontSize: 14,
    color: '#0A7C52',
    fontWeight: '700',
    marginTop: 4,
  },
  logMacroChips: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  logMacroChip: {
    fontSize: 12,
    color: '#4D6359',
    backgroundColor: '#EDF4F0',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    fontWeight: '600',
  },
  logTime: {
    fontSize: 12,
    color: '#74877E',
    fontWeight: '600',
  },
});
