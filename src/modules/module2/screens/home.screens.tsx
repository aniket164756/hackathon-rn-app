import React from 'react';
import { View } from 'react-native';
import { IBLButton, IBLText } from '../../../core-components';
import styles from '../styles/home.styles';
import { NavigationProp, ParamListBase } from '@react-navigation/core';

interface IProps {
  navigation?: NavigationProp<ParamListBase>;
}


const HomeScreen = (props: IProps) => {
  return (
    <View style={styles.container}>
      <IBLText displayText="This is Module 2 home screen" />
      <IBLButton
        buttonText="About"
        onPress={() => props.navigation?.navigate('About')}
      />
    </View>
  );
};

export default HomeScreen;
