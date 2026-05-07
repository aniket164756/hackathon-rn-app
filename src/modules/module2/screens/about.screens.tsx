import React from 'react';
import { View } from 'react-native';
import { IBLButton, IBLText } from '../../../core-components';
import styles from '../styles/about.styles';
import { NavigationProp, ParamListBase } from '@react-navigation/core';

interface IProps {
  navigation?: NavigationProp<ParamListBase>;
}
    

const AboutScreen = (props: IProps) => {
  return (
    <View style={styles.container}>
      <IBLText displayText="This is Module 2 about screen" />
      <IBLButton
        buttonText="Module 1 Home"
        onPress={() =>
          props.navigation?.navigate('Module1', { screen: 'Home' })
        }
      />
    </View>
  );
};

export default AboutScreen;
