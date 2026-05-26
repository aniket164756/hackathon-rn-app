import React, { useCallback } from 'react';
import { View } from 'react-native';
import { IBLButton, IBLText } from '../../../core-components';
import styles from '../styles/about.style';
import { NavigationProp, ParamListBase } from '@react-navigation/native';

interface IProps {
  navigation?: NavigationProp<ParamListBase>;
}

const AboutScreen = (props: IProps) => {
  const onButtonPress = useCallback(() => {
    props.navigation?.navigate('Module2', { screen: 'Home' });
  }, [props.navigation]);

  return (
    <View style={styles.container}>
      <IBLText displayText="This is Module 2 home screen" />
      <IBLButton buttonText="Module 2 Home" onPress={onButtonPress} />
    </View>
  );
};

export default AboutScreen;
