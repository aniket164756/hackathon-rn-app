import React, { useCallback } from 'react';
import { View } from 'react-native';
import { IBLButton, IBLText } from '../../../core-components';
import styles from '../styles/home.style';
import { NavigationProp, ParamListBase } from '@react-navigation/native';

interface IProps {
  navigation?: NavigationProp<ParamListBase>;
}

const HomeScreen = (props: IProps) => {
  const onButtonPress = useCallback(() => {
    props.navigation?.navigate('About');
  }, [props.navigation]);

  return (
    <View style={styles.container}>
      <IBLText displayText="This is Module 1 home screen" />
      <IBLButton buttonText="About" onPress={onButtonPress} />
    </View>
  );
};

export default HomeScreen;
