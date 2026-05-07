import React from 'react';
import { Text, TouchableOpacity } from 'react-native';
import styles from './IBL-Button.style';

interface IProps {
  buttonText: any;
  onPress: () => any;
}

const IBLButton = (props: IProps) => {
  return (
    <TouchableOpacity onPress={props.onPress} style={styles.buttonContainer}>
      <Text style={styles.textColor}>{props.buttonText}</Text>
    </TouchableOpacity>
  );
};

export default IBLButton;
