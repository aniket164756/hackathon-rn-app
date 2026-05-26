import React, { useCallback } from 'react';
import { View } from 'react-native';
import { IBLButton, IBLText } from '../../../core-components';
import styles from '../styles/about.style';
import { NavigationProp, ParamListBase } from '@react-navigation/core';

interface IProps {
  navigation?: NavigationProp<ParamListBase>;
}

const AboutScreen = (props: IProps) => {
  const onButtonPress = useCallback(() => {
    props.navigation?.navigate('Module1', { screen: 'Home' });
  }, [props.navigation]);
  
  return (
    <View style={styles.container}>
      <IBLText displayText="This is Module 2 about screen" />
      <IBLButton
        buttonText="Module 1 Home"
        onPress={onButtonPress}
      />
    </View>
  );
};

export default AboutScreen;
