import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from '../screens/home.screens';
import AboutScreen from '../screens/about.screens';

export type Module1StackParamList = {
  Home: undefined;
  About: undefined;
};

const Stack = createNativeStackNavigator<Module1StackParamList>();

const Module1Navigator = () => {
  return (
    <Stack.Navigator initialRouteName="Home">
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="About" component={AboutScreen} />
    </Stack.Navigator>
  );
};

export default Module1Navigator;
