import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from '../screens/home.screens';
import AboutScreen from '../screens/about.screens';

export type Module2StackParamList = {
  Home: undefined;
  About: undefined;
};

const Stack = createNativeStackNavigator<Module2StackParamList>();

const Module2Navigator = () => {
  return (
    <Stack.Navigator initialRouteName="Home">
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="About" component={AboutScreen} />
    </Stack.Navigator>
  );
};

export default Module2Navigator;
