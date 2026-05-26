import { StyleSheet } from 'react-native';
import PALETTE from '../../core-constants/palette.constant';

const styles = StyleSheet.create({
  buttonContainer: {
    borderRadius: 8,
    backgroundColor: PALETTE.primary,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  textColor: {
    color: PALETTE.onPrimary,
    textAlign: 'center',
    fontWeight: 'bold',
    fontSize: 16,
  },
});

export default styles;
