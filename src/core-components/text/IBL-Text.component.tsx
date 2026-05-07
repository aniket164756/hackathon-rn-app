import React from 'react';
import { Text } from 'react-native';
import styles from './IBL-Text.style';

interface IProps {
  displayText: any;
}

const IBLText = (props: IProps) => {
  return <Text style={styles.textColor}>{props.displayText}</Text>;
};

export default IBLText;
