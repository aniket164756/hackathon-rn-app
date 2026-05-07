import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import Module1Navigator from '../modules/module1/navigations/module1.navigation';
import Module2Navigator from '../modules/module2/navigations/module2.navigation';

export type RootStackParamList = {
  Module1: undefined;
  Module2: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const CoreNavigation = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Module1">
        <Stack.Screen
          name="Module1"
          component={Module1Navigator}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Module2"
          component={Module2Navigator}
          options={{ headerShown: false }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default CoreNavigation;
